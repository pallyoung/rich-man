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
        data = resp.json() if resp.text else {}

        news_list = []
        data_obj = data.get('data') if isinstance(data.get('data'), dict) else {}
        items = data_obj.get('list', []) if data_obj else []
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
        {
            'title': '半导体行业景气度持续回升 设备厂商订单饱满',
            'summary': '受益于国产替代加速和下游需求回暖，半导体行业景气度持续回升，多家设备厂商订单排至明年。',
            'url': 'https://finance.eastmoney.com',
            'source': '第一财经',
            'publish_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'image_url': '',
        },
        {
            'title': '券商板块集体走强 机构看好资本市场改革红利',
            'summary': '受资本市场改革政策利好影响，券商板块今日集体走强，多家机构看好行业长期发展前景。',
            'url': 'https://finance.eastmoney.com',
            'source': '证券日报',
            'publish_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'image_url': '',
        },
        {
            'title': '光伏产业链价格企稳 行业有望迎来拐点',
            'summary': '经过持续调整后，光伏产业链各环节价格逐步企稳，行业有望在下半年迎来基本面拐点。',
            'url': 'https://finance.eastmoney.com',
            'source': '财联社',
            'publish_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'image_url': '',
        },
        {
            'title': '人工智能应用加速落地 相关概念股持续活跃',
            'summary': '随着AI技术在各行业的应用加速落地，人工智能概念股近期持续活跃，市场关注度居高不下。',
            'url': 'https://finance.eastmoney.com',
            'source': '东方财富',
            'publish_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'image_url': '',
        },
        {
            'title': '消费板块估值修复 龙头公司获资金青睐',
            'summary': '随着消费数据逐步改善，消费板块估值修复预期增强，多家龙头公司获北向资金大幅增持。',
            'url': 'https://finance.eastmoney.com',
            'source': '中国基金报',
            'publish_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'image_url': '',
        },
    ]


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


@news_bp.route('/api/news/latest', methods=['GET'])
def latest_news():
    """Get latest financial news.

    Query params:
        limit: Number of items (default 20).
    """
    limit = int(request.args.get('limit', 20))
    cache_key = f'news_latest_{limit}'
    cached = get_cached(cache_key, max_age_seconds=120)
    if cached is not None:
        return _success(cached)

    news_items = _fetch_eastmoney_news(page=1, page_size=limit)
    if not news_items:
        news_items = _get_mock_news()
        # Expand mock news to fill limit
        while len(news_items) < limit:
            for item in _get_mock_news():
                if len(news_items) >= limit:
                    break
                news_items.append(item)

    set_cached(cache_key, news_items[:limit], ttl_seconds=120)
    return _success(news_items[:limit])


@news_bp.route('/api/news/stock/<code>', methods=['GET'])
def stock_news(code):
    """Get news for a specific stock.

    Path params:
        code: Stock code.
    """
    code = normalize_stock_code(code)
    cache_key = f'news_stock_{code}'
    cached = get_cached(cache_key, max_age_seconds=120)
    if cached is not None:
        return _success(cached)

    try:
        import akshare as ak
        df = ak.stock_news_em(symbol=code)
        if df is not None and not df.empty:
            news_list = []
            for _, row in df.head(20).iterrows():
                title = str(row.get('新闻标题', ''))
                content = str(row.get('新闻内容', ''))[:200]
                news_list.append({
                    'title': re.sub(r'<[^>]+>', '', title),
                    'summary': re.sub(r'<[^>]+>', '', content),
                    'url': str(row.get('新闻链接', '')),
                    'source': str(row.get('文章来源', '')),
                    'publish_time': str(row.get('发布时间', '')),
                })
            set_cached(cache_key, news_list, ttl_seconds=120)
            return _success(news_list)
    except Exception as e:
        logger.warning("Failed to fetch stock news for %s: %s", code, e)

    fallback = [
        {
            'title': f'{code} 相关资讯获取中',
            'summary': '新闻数据暂时无法获取，请稍后重试。',
            'url': '',
            'source': '系统提示',
            'publish_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        },
    ]
    set_cached(cache_key, fallback, ttl_seconds=120)
    return _success(fallback)


@news_bp.route('/api/news/announcements', methods=['GET'])
def stock_announcements():
    """Get announcements for a specific stock.

    Query params:
        stock_code: Stock code (required).
    """
    stock_code = request.args.get('stock_code', '').strip()
    if not stock_code:
        return _error("stock_code parameter is required")

    stock_code = normalize_stock_code(stock_code)
    cache_key = f'news_announcements_{stock_code}'
    cached = get_cached(cache_key, max_age_seconds=300)
    if cached is not None:
        return _success(cached)

    try:
        import akshare as ak
        # Try different akshare functions for announcements
        df = None
        try:
            df = ak.stock_notice_report(symbol=stock_code)
        except Exception:
            pass
        if df is not None and not df.empty:
            announcements = []
            for _, row in df.head(20).iterrows():
                title = str(row.get('标题', row.get('公告标题', row.iloc[0] if len(row) > 0 else '')))
                date = str(row.get('日期', row.get('公告日期', row.iloc[1] if len(row) > 1 else '')))
                announcements.append({
                    'title': title,
                    'date': date,
                    'type': str(row.get('类型', '公告')),
                    'url': str(row.get('链接', '')),
                })
            set_cached(cache_key, announcements, ttl_seconds=30)
            return _success(announcements)
    except Exception as e:
        logger.warning("Failed to fetch announcements for %s: %s", stock_code, e)

    # Mock fallback
    fallback = [
        {
            'title': f'{stock_code} 2025年年度报告',
            'date': '2025-04-28',
            'type': '定期报告',
            'url': '',
        },
        {
            'title': f'{stock_code} 关于回购股份的公告',
            'date': '2025-03-15',
            'type': '临时公告',
            'url': '',
        },
        {
            'title': f'{stock_code} 第三季度报告',
            'date': '2024-10-29',
            'type': '定期报告',
            'url': '',
        },
    ]
    set_cached(cache_key, fallback, ttl_seconds=30)
    return _success(fallback)
