"""Market data API blueprint.

Provides endpoints for market overview, stock rankings,
sector data, and limit-up/limit-down information.
"""

import logging
from datetime import datetime

import pandas as pd
import requests
from flask import Blueprint, request, jsonify

from services.cache import get_cached, set_cached

logger = logging.getLogger(__name__)

market_bp = Blueprint('market', __name__)

# Major index codes and names
MAJOR_INDICES = {
    '000001': '上证指数',
    '399001': '深证成指',
    '399006': '创业板指',
    '000688': '科创50',
}

# Mock/fallback data for when akshare is unavailable
MOCK_INDICES = [
    {
        'code': '000001',
        'name': '上证指数',
        'price': 3150.28,
        'change': 15.36,
        'change_pct': 0.49,
        'volume': 324500000000,
        'amount': 385600000000,
    },
    {
        'code': '399001',
        'name': '深证成指',
        'price': 10280.56,
        'change': -42.18,
        'change_pct': -0.41,
        'volume': 412300000000,
        'amount': 456700000000,
    },
    {
        'code': '399006',
        'name': '创业板指',
        'price': 2045.33,
        'change': 8.72,
        'change_pct': 0.43,
        'volume': 198700000000,
        'amount': 234500000000,
    },
    {
        'code': '000688',
        'name': '科创50',
        'price': 980.15,
        'change': -3.25,
        'change_pct': -0.33,
        'volume': 56700000000,
        'amount': 78900000000,
    },
]


def _success(data, message="success"):
    """Create a success response."""
    return jsonify({"code": 0, "data": data, "message": message})


def _error(message, code=-1):
    """Create an error response."""
    return jsonify({"code": code, "data": None, "message": message})



def _fetch_market_breadth() -> dict:
    """Fetch real-time A-share market breadth from East Money.

    Returns dict with up_count, down_count, flat_count from the
    Shanghai and Shenzhen markets combined. Falls back to empty dict
    on failure.
    """
    try:
        url = "https://push2.eastmoney.com/api/qt/ulist.np/get"
        # secids: 1.000001 = Shanghai composite, 0.399001 = Shenzhen component
        # f104 = up count, f105 = down count, f106 = flat count
        params = {
            'fltt': '2',
            'secids': '1.000001,0.399001',
            'fields': 'f104,f105,f106',
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://quote.eastmoney.com/',
        }
        resp = requests.get(url, params=params, headers=headers, timeout=8)
        resp.raise_for_status()
        data = resp.json()

        diff = data.get('data', {}).get('diff', [])
        if not diff:
            return {}

        # Sum up counts from both markets
        up_total = sum(item.get('f104', 0) for item in diff if item.get('f104'))
        down_total = sum(item.get('f105', 0) for item in diff if item.get('f105'))
        flat_total = sum(item.get('f106', 0) for item in diff if item.get('f106'))

        if up_total + down_total + flat_total == 0:
            return {}

        return {
            'up_count': up_total,
            'down_count': down_total,
            'flat_count': flat_total,
        }
    except Exception as e:
        logger.warning("Failed to fetch market breadth from East Money: %s", e)
        return {}



def _compute_fear_greed(up_count: int, down_count: int, flat_count: int,
                         indices: list = None) -> dict:
    """Compute a multi-factor Fear & Greed Index.

    Factors:
        1. Market breadth (up/down ratio) - 40% weight
        2. Index momentum (avg change % of major indices) - 35% weight
        3. Advance/decline strength (extreme moves ratio) - 25% weight

    Returns dict with score (0-100), label, and factor breakdown.
    0 = extreme fear, 50 = neutral, 100 = extreme greed.
    """
    total = up_count + down_count + flat_count

    # Factor 1: Market breadth (up ratio mapped to 0-100)
    breadth_ratio = (up_count / total * 100) if total > 0 else 50.0

    # Factor 2: Index momentum
    momentum_score = 50.0
    if indices:
        changes = [idx.get('change_pct', 0) for idx in indices if idx.get('change_pct') is not None]
        if changes:
            avg_change = sum(changes) / len(changes)
            # Map: -3% -> 10, 0% -> 50, +3% -> 90
            momentum_score = max(0, min(100, 50 + avg_change * 13.3))

    # Factor 3: Advance/decline strength
    # Measures how lopsided the market is
    strength_score = 50.0
    if total > 0:
        # Strong advance: many more up than down
        # Strong decline: many more down than up
        imbalance = (up_count - down_count) / total * 100
        # Map: -100% -> 0, 0% -> 50, +100% -> 100
        strength_score = max(0, min(100, 50 + imbalance * 0.5))

    # Weighted composite
    score = round(breadth_ratio * 0.40 + momentum_score * 0.35 + strength_score * 0.25, 1)
    score = max(0, min(100, score))

    # Label
    if score <= 20:
        label = '极度恐惧'
    elif score <= 35:
        label = '恐惧'
    elif score <= 45:
        label = '偏恐惧'
    elif score <= 55:
        label = '中性'
    elif score <= 65:
        label = '偏贪婪'
    elif score <= 80:
        label = '贪婪'
    else:
        label = '极度贪婪'

    return {
        'score': score,
        'label': label,
        'factors': {
            'breadth': {'score': round(breadth_ratio, 1), 'weight': 0.40,
                        'label': '涨跌比'},
            'momentum': {'score': round(momentum_score, 1), 'weight': 0.35,
                         'label': '指数动量'},
            'strength': {'score': round(strength_score, 1), 'weight': 0.25,
                         'label': '涨跌强度'},
        },
    }


@market_bp.route('/api/market/overview', methods=['GET'])
def market_overview():
    """Get major market index data.

    Returns current price, change, and change percentage for
    上证指数, 深证成指, 创业板指, 科创50.
    """
    cache_key = 'market_overview'
    cached = get_cached(cache_key, max_age_seconds=30)
    if cached is not None:
        return _success(cached)

    try:
        from services.stock_data import get_market_overview
        indices = get_market_overview()

        if not indices:
            return _error("暂无指数数据")

        set_cached(cache_key, indices, ttl_seconds=30)
        return _success(indices)

    except Exception as e:
        logger.warning("Failed to fetch market overview: %s", e)
        return _error("暂无指数数据")


@market_bp.route('/api/market/ranking', methods=['GET'])
def stock_ranking():
    """Get stock ranking by various criteria.

    Query params:
        type: 'rise' (default), 'fall', 'turnover', 'volume'
        page: Page number (default 1)
        page_size: Items per page (default 20)
    """
    rank_type = request.args.get('type', 'rise')
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))

    cache_key = f'market_ranking_{rank_type}_{page}_{page_size}'
    cached = get_cached(cache_key, max_age_seconds=60)
    if cached is not None:
        return _success(cached)

    try:
        from services.stock_data import bs_query, _code_to_bs
        from services.mock_data import MOCK_STOCKS
        import baostock as bs

        # Get latest data for a pool of well-known stocks
        stocks = []
        for s in MOCK_STOCKS:
            code = s['code']
            try:
                bs_code = _code_to_bs(code)
                from datetime import datetime, timedelta
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
                rows = bs_query(
                    bs.query_history_k_data_plus,
                    bs_code, "date,close,high,low,volume,amount,pctChg,turn",
                    start_date=start_date, end_date=end_date,
                    frequency="d", adjustflag="2",
                )
                if rows:
                    latest = rows[-1]
                    prev = rows[-2] if len(rows) > 1 else latest
                    price = _safe_float(latest[1])
                    prev_close = _safe_float(prev[1])
                    change = round(price - prev_close, 2) if prev_close else 0
                    change_pct = _safe_float(latest[6])
                    stocks.append({
                        'code': code,
                        'name': s['name'],
                        'price': price,
                        'change': change,
                        'change_pct': change_pct,
                        'volume': _safe_float(latest[4]),
                        'turnover': _safe_float(latest[5]),
                        'turnover_rate': _safe_float(latest[7]),
                        'pe': 0,
                        'market_cap': 0,
                    })
            except Exception:
                pass

        # Sort by ranking type
        if rank_type == 'rise':
            stocks.sort(key=lambda x: x.get('change_pct', 0), reverse=True)
        elif rank_type == 'fall':
            stocks.sort(key=lambda x: x.get('change_pct', 0))
        elif rank_type == 'turnover':
            stocks.sort(key=lambda x: x.get('turnover', 0), reverse=True)
        elif rank_type == 'volume':
            stocks.sort(key=lambda x: x.get('volume', 0), reverse=True)

        total = len(stocks)
        start = (page - 1) * page_size
        end = start + page_size

        result = {
            'total': total,
            'page': page,
            'page_size': page_size,
            'stocks': stocks[start:end],
        }

        set_cached(cache_key, result, ttl_seconds=60)
        return _success(result)

    except Exception as e:
        logger.warning("Failed to fetch stock ranking: %s", e)
        return _error("暂无排行数据")




@market_bp.route('/api/market/limit-up', methods=['GET'])
def limit_up():
    """Get stocks that hit the daily limit-up (涨停板)."""
    cache_key = 'market_limit_up'
    cached = get_cached(cache_key, max_age_seconds=60)
    if cached is not None:
        return _success(cached)

    try:
        import akshare as ak
        today = datetime.now().strftime('%Y%m%d')
        df = ak.stock_zt_pool_em(date=today)

        stocks = []
        if df is not None and not df.empty:
            for _, row in df.iterrows():
                stock = {
                    'code': str(row.get('代码', '')),
                    'name': str(row.get('名称', '')),
                    'price': _safe_float(row.get('最新价')),
                    'change_pct': _safe_float(row.get('涨跌幅')),
                    'turnover': _safe_float(row.get('成交额')),
                    'turnover_rate': _safe_float(row.get('换手率')),
                    'limit_up_reason': str(row.get('涨停原因', '')),
                    'first_limit_time': str(row.get('首次封板时间', '')),
                    'last_limit_time': str(row.get('最后封板时间', '')),
                    'open_count': int(_safe_float(row.get('炸板次数', 0))),
                    'streak': int(_safe_float(row.get('连板数', 1))),
                }
                stocks.append(stock)

        set_cached(cache_key, stocks, ttl_seconds=60)
        return _success(stocks)

    except Exception as e:
        logger.warning("Failed to fetch limit-up data: %s", e)
        return _success([])


@market_bp.route('/api/market/limit-down', methods=['GET'])
def limit_down():
    """Get stocks that hit the daily limit-down (跌停板)."""
    cache_key = 'market_limit_down'
    cached = get_cached(cache_key, max_age_seconds=60)
    if cached is not None:
        return _success(cached)

    try:
        import akshare as ak
        today = datetime.now().strftime('%Y%m%d')
        df = ak.stock_zt_pool_dtgc_em(date=today)

        stocks = []
        if df is not None and not df.empty:
            for _, row in df.iterrows():
                stock = {
                    'code': str(row.get('代码', '')),
                    'name': str(row.get('名称', '')),
                    'price': _safe_float(row.get('最新价')),
                    'change_pct': _safe_float(row.get('涨跌幅')),
                    'turnover': _safe_float(row.get('成交额')),
                    'turnover_rate': _safe_float(row.get('换手率')),
                    'limit_down_reason': str(row.get('跌停原因', '')),
                    'first_limit_time': str(row.get('首次封板时间', '')),
                }
                stocks.append(stock)

        set_cached(cache_key, stocks, ttl_seconds=60)
        return _success(stocks)

    except Exception as e:
        logger.warning("Failed to fetch limit-down data: %s", e)
        return _success([])


def _safe_float(value, default=0.0):
    """Safely convert a value to float."""
    if value is None or value == '' or value == '-':
        return default
    try:
        import math
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            return default
        return round(result, 2)
    except (ValueError, TypeError):
        return default


@market_bp.route('/api/market/updown_stats', methods=['GET'])
def market_updown_stats():
    """Get market up/down/flat stock counts and sentiment.

    Uses real-time East Money data for full A-share market breadth.
    Falls back to baostock sample data if East Money is unavailable.
    """
    cache_key = 'market_updown_stats'
    cached = get_cached(cache_key, max_age_seconds=60)
    if cached is not None:
        return _success(cached)

    # Try real-time East Money market breadth first
    breadth = _fetch_market_breadth()
    if breadth:
        up_count = breadth['up_count']
        down_count = breadth['down_count']
        flat_count = breadth['flat_count']
    else:
        # Fallback: sample from baostock using MOCK_STOCKS
        try:
            from services.stock_data import bs_query, _code_to_bs
            from services.mock_data import MOCK_STOCKS
            import baostock as bs
            from datetime import timedelta

            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')

            up_count = 0
            down_count = 0
            flat_count = 0

            for s in MOCK_STOCKS:
                try:
                    bs_code = _code_to_bs(s['code'])
                    rows = bs_query(
                        bs.query_history_k_data_plus,
                        bs_code, "date,pctChg",
                        start_date=start_date, end_date=end_date,
                        frequency="d", adjustflag="2",
                    )
                    if rows:
                        change = float(rows[-1][1]) if rows[-1][1] else 0
                        if change > 0:
                            up_count += 1
                        elif change < 0:
                            down_count += 1
                        else:
                            flat_count += 1
                except Exception:
                    pass
        except Exception as e:
            logger.warning("Failed to fetch updown stats from baostock: %s", e)
            return _error("暂无涨跌统计数据")

    # Get index data for momentum factor
    indices = []
    try:
        from services.stock_data import get_market_overview
        indices = get_market_overview() or []
    except Exception:
        pass

    # Compute multi-factor fear & greed index
    fg = _compute_fear_greed(up_count, down_count, flat_count, indices)

    result = {
        'up_count': up_count,
        'down_count': down_count,
        'flat_count': flat_count,
        'sentiment': fg['score'],
        'sentiment_label': fg['label'],
        'factors': fg['factors'],
        'source': 'eastmoney' if breadth else 'baostock_sample',
    }
    set_cached(cache_key, result, ttl_seconds=120)
    return _success(result)



@market_bp.route('/api/market/fear_greed', methods=['GET'])
def fear_greed_index():
    """Get detailed Fear & Greed Index with factor breakdown.

    Returns composite score (0-100) and individual factor scores:
    - breadth: market up/down ratio
    - momentum: major index average change %
    - strength: advance/decline imbalance
    """
    cache_key = 'market_fear_greed'
    cached = get_cached(cache_key, max_age_seconds=60)
    if cached is not None:
        return _success(cached)

    # Get market breadth
    breadth = _fetch_market_breadth()
    if not breadth:
        # Fallback to updown_stats cache
        ud_cached = get_cached('market_updown_stats', max_age_seconds=120)
        if ud_cached:
            breadth = ud_cached
        else:
            return _error('暂无市场数据')

    up_count = breadth.get('up_count', 0)
    down_count = breadth.get('down_count', 0)
    flat_count = breadth.get('flat_count', 0)

    # Get index momentum
    indices = []
    try:
        from services.stock_data import get_market_overview
        indices = get_market_overview() or []
    except Exception:
        pass

    fg = _compute_fear_greed(up_count, down_count, flat_count, indices)

    result = {
        'score': fg['score'],
        'label': fg['label'],
        'factors': fg['factors'],
        'market_breadth': {
            'up_count': up_count,
            'down_count': down_count,
            'flat_count': flat_count,
        },
        'indices': [{'name': i.get('name'), 'change_pct': i.get('change_pct')} for i in indices],
    }
    set_cached(cache_key, result, ttl_seconds=120)
    return _success(result)


@market_bp.route('/api/market/sectors', methods=['GET'])
def market_sectors():
    """Get sector data (alias for sector heatmap)."""
    cache_key = 'market_sectors'
    cached = get_cached(cache_key, max_age_seconds=120)
    if cached is not None:
        return _success(cached)

    try:
        from services.stock_data import bs_query, _code_to_bs, _safe_float as bs_safe_float
        from services.mock_data import MOCK_STOCKS
        import baostock as bs
        from collections import defaultdict
        from datetime import datetime, timedelta

        # Get industry classification from baostock
        industry_rows = bs_query(bs.query_stock_industry)
        industry_map = {}
        for row in industry_rows:
            code_num = row[1].split('.')[-1] if '.' in row[1] else row[1]
            industry_name = row[3] if len(row) > 3 else ''
            if industry_name:
                industry_map[code_num] = industry_name

        # Get latest data for a small representative stock sample
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')

        industry_data = defaultdict(lambda: {'stocks': [], 'up': 0, 'down': 0, 'total_change': 0})

        # Use a smaller sample for speed (first 15 stocks from MOCK_STOCKS)
        sample = MOCK_STOCKS[:15]
        for s in sample:
            code = s['code']
            industry = industry_map.get(code, '其他')
            try:
                bs_code = _code_to_bs(code)
                rows = bs_query(
                    bs.query_history_k_data_plus,
                    bs_code, "date,close,pctChg",
                    start_date=start_date, end_date=end_date,
                    frequency="d", adjustflag="2",
                )
                if rows:
                    latest = rows[-1]
                    change_pct = bs_safe_float(latest[2])
                    price = bs_safe_float(latest[1])
                    industry_data[industry]['stocks'].append({
                        'code': code, 'name': s['name'],
                        'price': price, 'change_pct': change_pct,
                    })
                    industry_data[industry]['total_change'] += change_pct
                    if change_pct > 0:
                        industry_data[industry]['up'] += 1
                    elif change_pct < 0:
                        industry_data[industry]['down'] += 1
            except Exception:
                pass

        # Build sector list
        sectors = []
        for name, data in industry_data.items():
            if not data['stocks']:
                continue
            avg_change = round(data['total_change'] / len(data['stocks']), 2)
            leading = max(data['stocks'], key=lambda x: x['change_pct'])
            sectors.append({
                'code': '',
                'name': name,
                'change_pct': avg_change,
                'market_cap': 0,
                'turnover_rate': 0,
                'up_count': data['up'],
                'down_count': data['down'],
                'leading_stock': leading['name'],
                'leading_change_pct': leading['change_pct'],
            })

        sectors.sort(key=lambda x: x['change_pct'], reverse=True)
        set_cached(cache_key, sectors, ttl_seconds=120)
        return _success(sectors)

    except Exception as e:
        logger.warning("Failed to fetch sector data: %s", e)
        return _error("暂无板块数据")


@market_bp.route('/api/market/hot', methods=['GET'])
def dragon_tiger_list():
    """Get Dragon Tiger list (龙虎榜) data.

    Returns stocks with unusual trading activity reported
    by the exchange, including institutional and hot money movements.
    """
    cache_key = 'market_dragon_tiger'
    cached = get_cached(cache_key, max_age_seconds=120)
    if cached is not None:
        return _success(cached)

    try:
        import akshare as ak
        today = datetime.now().strftime('%Y%m%d')
        df = ak.stock_lhb_detail_em(start_date=today, end_date=today)

        if df is not None and not df.empty:
            col_map = {
                '代码': 'code',
                '名称': 'name',
                '收盘价': 'price',
                '涨跌幅': 'change_pct',
                '龙虎榜净买额': 'net_buy',
                '龙虎榜买入额': 'buy_amount',
                '龙虎榜卖出额': 'sell_amount',
                '上榜原因': 'reason',
            }
            available_cols = {k: v for k, v in col_map.items() if k in df.columns}
            df = df.rename(columns=available_cols)

            stocks = []
            for _, row in df.iterrows():
                stocks.append({
                    'code': str(row.get('code', '')),
                    'name': str(row.get('name', '')),
                    'price': _safe_float(row.get('price')),
                    'change_pct': _safe_float(row.get('change_pct')),
                    'net_buy': _safe_float(row.get('net_buy')),
                    'buy_amount': _safe_float(row.get('buy_amount')),
                    'sell_amount': _safe_float(row.get('sell_amount')),
                    'reason': str(row.get('reason', '')),
                })

            set_cached(cache_key, stocks, ttl_seconds=120)
            return _success(stocks)
    except Exception as e:
        logger.warning("Failed to fetch Dragon Tiger list: %s, using mock", e)

    return _error("暂无龙虎榜数据")
