"""News API blueprint.

Provides endpoints for financial news, stock-specific news,
and market sentiment analysis.
"""

import logging
import re
from datetime import datetime

import requests
from flask import Blueprint, request, jsonify

from services.cache import get_cached, set_cached
from utils.stock_utils import normalize_stock_code

logger = logging.getLogger(__name__)

news_bp = Blueprint('news', __name__)

# Positive and negative keywords for sentiment analysis
POSITIVE_KEYWORDS = [
    '利好', '上涨', '增长', '突破', '新高', '大涨', '暴涨', '涨停',
    '反弹', '回暖', '利多', '看多', '牛市', '强势', '回升', '拉升',
    '复苏', '景气', '盈利', '分红', '增持', '买入', '推荐', '乐观',
    '超预期', '创新高', '放量', '领涨', '强势', '红盘', '提振',
]

NEGATIVE_KEYWORDS = [
    '利空', '下跌', '下降', '暴跌', '跌停', '新低', '亏损', '风险',
    '减持', '卖出', '熊市', '看空', '弱势', '回落', '回调', '下行',
    '低迷', '衰退', '违约', '爆雷', '退市', '警告', '处罚', '悲观',
    '低于预期', '缩量', '领跌', '绿盘', '承压', '疲软', '萎缩',
]


def _success(data, message="success"):
    """Create a success response."""
    return jsonify({"code": 0, "data": data, "message": message})


def _error(message, code=-1):
    """Create an error response."""
    return jsonify({"code": code, "data": None, "message": message})


def _fetch_eastmoney_news(page: int = 1, page_size: int = 20) -> list:
    """Fetch financial news from East Money (东方财富).

    Uses the East Money news API to get latest financial news.

    Args:
        page: Page number (1-based).
        page_size: Number of items per page.

    Returns:
        List of news items.
    """
    try:
        url = "https://np-listapi.eastmoney.com/comm/web/getNewsByColumns"
        params = {
            'client': 'web',
            'biz': 'web_news_col',
            'column': '350',
            'order': '1',
            'needInteractData': '0',
            'page_index': page,
            'page_size': page_size,
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://finance.eastmoney.com/',
        }

        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        news_list = []
        items = data.get('data', {}).get('list', [])
        for item in items:
            news = {
                'title': item.get('title', ''),
                'summary': item.get('digest', item.get('content', ''))[:200],
                'url': item.get('url', ''),
                'source': item.get('source', '东方财富'),
                'publish_time': item.get('showtime', ''),
                'image_url': item.get('imgurl', ''),
            }
            # Clean HTML tags from summary
            news['summary'] = re.sub(r'<[^>]+>', '', news['summary'])
            news_list.append(news)

        return news_list

    except Exception as e:
        logger.warning("Failed to fetch news from East Money: %s", e)
        return []


def _get_mock_news() -> list:
    """Return mock news data as fallback."""
    return [
        {
            'title': 'A股三大指数集体收涨 半导体板块领涨',
            'summary': '今日A股市场三大指数集体收涨，半导体板块涨幅居前，多只个股涨停。市场成交额突破万亿，北向资金大幅净流入。',
            'url': 'https://finance.eastmoney.com',
            'source': '东方财富',
            'publish_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'image_url': '',
        },
        {
            'title': '央行：保持流动性合理充裕 支持实体经济发展',
            'summary': '中国人民银行表示将继续实施稳健的货币政策，保持流动性合理充裕，加大对实体经济的支持力度。',
            'url': 'https://finance.eastmoney.com',
            'source': '新华财经',
            'publish_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'image_url': '',
        },
        {
            'title': '新能源汽车销量持续增长 产业链公司受益',
            'summary': '最新数据显示新能源汽车月度销量再创新高，渗透率持续提升，产业链上下游公司有望持续受益。',
            'url': 'https://finance.eastmoney.com',
            'source': '证券时报',
            'publish_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'image_url': '',
        },
        {
            'title': '北向资金今日净买入超50亿元 重点加仓科技股',
            'summary': '北向资金今日大幅净买入超50亿元，主要加仓电子、计算机等科技板块个股。',
            'url': 'https://finance.eastmoney.com',
            'source': '中国证券报',
            'publish_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'image_url': '',
        },
        {
            'title': '多家上市公司发布业绩预增公告 市场关注度提升',
            'summary': '临近财报季，多家上市公司发布业绩预增公告，部分公司业绩超预期增长引发市场关注。',
            'url': 'https://finance.eastmoney.com',
            'source': '上海证券报',
            'publish_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'image_url': '',
        },
    ]


@news_bp.route('/api/news/latest', methods=['GET'])
def latest_news():
    """Get latest financial news.

    Query params:
        page: Page number (default 1)
        page_size: Items per page (default 20)
    """
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))

    cache_key = f'news_latest_{page}_{page_size}'
    cached = get_cached(cache_key, max_age_seconds=120)
    if cached is not None:
        return _success(cached)

    # Try to fetch real news
    news = _fetch_eastmoney_news(page, page_size)

    if not news:
        # Fallback to mock data
        news = _get_mock_news()

    result = {
        'page': page,
        'page_size': page_size,
        'news': news,
    }

    set_cached(cache_key, result, ttl_seconds=120)
    return _success(result)


@news_bp.route('/api/news/stock/<code>', methods=['GET'])
def stock_news(code):
    """Get stock-specific news.

    Path params:
        code: Stock code
    """
    code = normalize_stock_code(code)

    cache_key = f'news_stock_{code}'
    cached = get_cached(cache_key, max_age_seconds=120)
    if cached is not None:
        return _success(cached)

    try:
        # Try East Money stock news API
        url = "https://search-api-web.eastmoney.com/search/jsonp"
        params = {
            'cb': 'jQuery',
            'param': (
                '{"uid":"","keyword":"' + code + '","type":["cmsArticleWebOld"],'
                '"client":"web","clientType":"web","clientVersion":"curr",'
                '"param":{"cmsArticleWebOld":{"searchScope":"default",'
                '"sort":"default","pageIndex":1,"pageSize":20,"preTag":"",'
                '"postTag":""}}}'
            ),
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://so.eastmoney.com/',
        }

        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()

        # Parse JSONP response
        text = resp.text
        json_str = text[text.index('(') + 1:text.rindex(')')]
        import json
        data = json.loads(json_str)

        news_list = []
        articles = data.get('result', {}).get('cmsArticleWebOld', {}).get('list', [])
        for item in articles:
            title = item.get('title', '')
            # Clean HTML tags
            title = re.sub(r'<[^>]+>', '', title)
            content = item.get('content', item.get('date', ''))
            content = re.sub(r'<[^>]+>', '', str(content))[:200]

            news_list.append({
                'title': title,
                'summary': content,
                'url': item.get('url', ''),
                'source': item.get('mediaName', ''),
                'publish_time': item.get('date', ''),
            })

        if not news_list:
            news_list = [
                {
                    'title': f'{code}相关资讯暂无数据',
                    'summary': '暂时没有找到该股票的相关新闻资讯，请稍后重试。',
                    'url': '',
                    'source': '系统提示',
                    'publish_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                },
            ]

        set_cached(cache_key, news_list, ttl_seconds=120)
        return _success(news_list)

    except Exception as e:
        logger.warning("Failed to fetch stock news for %s: %s", code, e)
        # Return fallback
        fallback = [
            {
                'title': f'{code}相关资讯获取失败',
                'summary': '新闻数据暂时无法获取，请稍后重试。',
                'url': '',
                'source': '系统提示',
                'publish_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            },
        ]
        set_cached(cache_key, fallback, ttl_seconds=120)
        return _success(fallback)


@news_bp.route('/api/news/sentiment', methods=['GET'])
def market_sentiment():
    """Get market sentiment index.

    Simple implementation: counts positive and negative keywords
    in recent news to derive a sentiment score.

    Returns:
        Sentiment index (0-100), distribution of positive/negative news,
        and individual news sentiment scores.
    """
    cache_key = 'news_sentiment'
    cached = get_cached(cache_key, max_age_seconds=300)
    if cached is not None:
        return _success(cached)

    # Fetch recent news
    news_items = _fetch_eastmoney_news(page=1, page_size=50)
    if not news_items:
        news_items = _get_mock_news()

    positive_count = 0
    negative_count = 0
    neutral_count = 0
    news_sentiments = []

    for item in news_items:
        title = item.get('title', '')
        summary = item.get('summary', '')
        text = title + ' ' + summary

        # Count positive and negative keywords
        pos_hits = sum(1 for kw in POSITIVE_KEYWORDS if kw in text)
        neg_hits = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text)

        if pos_hits > neg_hits:
            sentiment = 'positive'
            positive_count += 1
        elif neg_hits > pos_hits:
            sentiment = 'negative'
            negative_count += 1
        else:
            sentiment = 'neutral'
            neutral_count += 1

        news_sentiments.append({
            'title': title,
            'sentiment': sentiment,
            'positive_hits': pos_hits,
            'negative_hits': neg_hits,
        })

    total = len(news_items)
    if total == 0:
        total = 1

    # Sentiment index: 0 (extremely bearish) to 100 (extremely bullish)
    # 50 is neutral
    sentiment_index = round(
        (positive_count / total * 100 * 0.7 + (total - negative_count) / total * 50 * 0.3),
        1
    )
    sentiment_index = max(0, min(100, sentiment_index))

    # Determine overall sentiment label
    if sentiment_index >= 70:
        sentiment_label = '极度乐观'
    elif sentiment_index >= 55:
        sentiment_label = '偏乐观'
    elif sentiment_index >= 45:
        sentiment_label = '中性'
    elif sentiment_index >= 30:
        sentiment_label = '偏悲观'
    else:
        sentiment_label = '极度悲观'

    result = {
        'sentiment_index': sentiment_index,
        'sentiment_label': sentiment_label,
        'positive_count': positive_count,
        'negative_count': negative_count,
        'neutral_count': neutral_count,
        'total_news': total,
        'positive_ratio': round(positive_count / total * 100, 1),
        'negative_ratio': round(negative_count / total * 100, 1),
        'news_sentiments': news_sentiments[:10],  # Top 10 for display
    }

    set_cached(cache_key, result, ttl_seconds=300)
    return _success(result)
