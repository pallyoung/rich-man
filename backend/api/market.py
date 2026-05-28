"""Market data API blueprint.

Provides endpoints for market overview, stock rankings,
sector data, and limit-up/limit-down information.
"""

import logging
from datetime import datetime

import pandas as pd
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
            indices = MOCK_INDICES

        set_cached(cache_key, indices, ttl_seconds=30)
        return _success(indices)

    except Exception as e:
        logger.warning("Failed to fetch market overview: %s", e)
        set_cached(cache_key, MOCK_INDICES, ttl_seconds=30)
        return _success(MOCK_INDICES)


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
        from services.stock_data import get_kline, get_stock_info, _ensure_login, _code_to_bs
        from services.mock_data import MOCK_STOCKS
        import baostock as bs

        _ensure_login()

        # Get latest data for a pool of well-known stocks
        stocks = []
        for s in MOCK_STOCKS:
            code = s['code']
            try:
                bs_code = _code_to_bs(code)
                from datetime import datetime, timedelta
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
                rs = bs.query_history_k_data_plus(
                    bs_code, "date,close,high,low,volume,amount,pctChg,turn",
                    start_date=start_date, end_date=end_date,
                    frequency="d", adjustflag="2"
                )
                rows = []
                while rs.next():
                    rows.append(rs.get_row_data())
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
        from services.mock_data import generate_ranking
        result = generate_ranking(rank_type, page, page_size)
        set_cached(cache_key, result, ttl_seconds=60)
        return _success(result)




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
    """Get market up/down/flat stock counts and sentiment."""
    cache_key = 'market_updown_stats'
    cached = get_cached(cache_key, max_age_seconds=60)
    if cached is not None:
        return _success(cached)

    try:
        import akshare as ak
        df = ak.stock_zh_a_spot_em()
        if df is not None and not df.empty:
            col = '涨跌幅'
            if col in df.columns:
                values = pd.to_numeric(df[col], errors='coerce').dropna()
                up_count = int((values > 0).sum())
                down_count = int((values < 0).sum())
                flat_count = int((values == 0).sum())
            else:
                up_count = down_count = flat_count = 0

            # Simple sentiment: based on up/down ratio
            total = up_count + down_count + flat_count
            if total > 0:
                sentiment = round((up_count / total) * 100, 1)
            else:
                sentiment = 50.0

            result = {
                'up_count': up_count,
                'down_count': down_count,
                'flat_count': flat_count,
                'sentiment': sentiment,
            }
            set_cached(cache_key, result, ttl_seconds=60)
            return _success(result)
    except Exception as e:
        logger.warning("Failed to fetch updown stats: %s, using mock", e)

    import random
    random.seed(42)
    result = {
        'up_count': random.randint(1500, 3000),
        'down_count': random.randint(1000, 2500),
        'flat_count': random.randint(100, 500),
        'sentiment': round(random.uniform(40, 65), 1),
    }
    set_cached(cache_key, result, ttl_seconds=60)
    return _success(result)


@market_bp.route('/api/market/sectors', methods=['GET'])
def market_sectors():
    """Get sector data (alias for sector heatmap)."""
    cache_key = 'market_sectors'
    cached = get_cached(cache_key, max_age_seconds=120)
    if cached is not None:
        return _success(cached)

    try:
        import akshare as ak
        df = ak.stock_board_industry_name_em()

        if df is None or df.empty:
            from services.mock_data import generate_sectors
            sectors = generate_sectors()
            set_cached(cache_key, sectors, ttl_seconds=120)
            return _success(sectors)

        col_map = {
            '板块名称': 'name',
            '板块代码': 'code',
            '涨跌幅': 'change_pct',
            '总市值': 'market_cap',
            '换手率': 'turnover_rate',
            '上涨家数': 'up_count',
            '下跌家数': 'down_count',
            '领涨股票': 'leading_stock',
            '领涨涨跌幅': 'leading_change_pct',
        }

        available_cols = {k: v for k, v in col_map.items() if k in df.columns}
        df = df.rename(columns=available_cols)
        df = df.sort_values('change_pct', ascending=False, na_position='last')

        sectors = []
        for _, row in df.iterrows():
            sector = {
                'code': str(row.get('code', '')),
                'name': str(row.get('name', '')),
                'change_pct': _safe_float(row.get('change_pct')),
                'market_cap': _safe_float(row.get('market_cap')),
                'turnover_rate': _safe_float(row.get('turnover_rate')),
                'up_count': int(_safe_float(row.get('up_count', 0))),
                'down_count': int(_safe_float(row.get('down_count', 0))),
                'leading_stock': str(row.get('leading_stock', '')),
                'leading_change_pct': _safe_float(row.get('leading_change_pct')),
            }
            sectors.append(sector)

        set_cached(cache_key, sectors, ttl_seconds=120)
        return _success(sectors)

    except Exception as e:
        logger.warning("Failed to fetch sector data: %s", e)
        from services.mock_data import generate_sectors
        sectors = generate_sectors()
        set_cached(cache_key, sectors, ttl_seconds=120)
        return _success(sectors)


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

    # Mock Dragon Tiger data
    import random
    from services.mock_data import MOCK_STOCKS
    random.seed(42)
    mock_data = []
    for s in random.sample(MOCK_STOCKS, min(10, len(MOCK_STOCKS))):
        mock_data.append({
            'code': s['code'],
            'name': s['name'],
            'price': round(s['base'] * random.uniform(0.95, 1.05), 2),
            'change_pct': round(random.uniform(-5, 10), 2),
            'net_buy': round(random.uniform(-5e8, 2e9), 2),
            'buy_amount': round(random.uniform(1e8, 3e9), 2),
            'sell_amount': round(random.uniform(1e8, 3e9), 2),
            'reason': random.choice(['日涨幅偏离值达7%', '日换手率达20%', '日振幅值达15%']),
        })
    set_cached(cache_key, mock_data, ttl_seconds=120)
    return _success(mock_data)
