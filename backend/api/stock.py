"""Stock analysis API blueprint.

Provides endpoints for K-line data, real-time quotes,
technical indicators, and fundamental data.
"""

import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from flask import Blueprint, request, jsonify

from services.cache import get_cached, set_cached
from services.indicators import calculate_all_indicators
from utils.stock_utils import normalize_stock_code, get_market_from_code

logger = logging.getLogger(__name__)

stock_bp = Blueprint('stock', __name__)


def _success(data, message="success"):
    """Create a success response."""
    return jsonify({"code": 0, "data": data, "message": message})


def _error(message, code=-1):
    """Create an error response."""
    return jsonify({"code": code, "data": None, "message": message})


def _safe_float(value, default=0.0):
    """Safely convert a value to float."""
    if value is None or value == '' or value == '-':
        return default
    try:
        result = float(value)
        if np.isnan(result) or np.isinf(result):
            return default
        return round(result, 2)
    except (ValueError, TypeError):
        return default


@stock_bp.route('/api/stock/<code>/kline', methods=['GET'])
def kline_data(code):
    """Get K-line (candlestick) data for a stock.

    Path params:
        code: Stock code (e.g., "000001", "sh600036")

    Query params:
        period: Data frequency - 'daily' (default), 'weekly', 'monthly'
        start_date: Start date in YYYYMMDD format
        end_date: End date in YYYYMMDD format
        adjust: Price adjustment - 'qfq' (forward, default), 'hfq' (backward), '' (none)
    """
    code = normalize_stock_code(code)
    period = request.args.get('period', 'daily')
    adjust = request.args.get('adjust', 'qfq')

    # Default date range: last 1 year
    end_date = request.args.get('end_date', datetime.now().strftime('%Y%m%d'))
    start_date = request.args.get(
        'start_date',
        (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
    )

    cache_key = f'stock_kline_{code}_{period}_{start_date}_{end_date}_{adjust}'
    cached = get_cached(cache_key, max_age_seconds=300)
    if cached is not None:
        return _success(cached)

    try:
        from services.stock_data import get_kline
        df = get_kline(code, start_date=start_date, end_date=end_date,
                       period=period, adjust=adjust)

        if df is None or df.empty:
            return _error(f"No K-line data found for stock {code}")

        kline = []
        for _, row in df.iterrows():
            entry = {
                'date': str(row.get('date', '')),
                'open': _safe_float(row.get('open')),
                'close': _safe_float(row.get('close')),
                'high': _safe_float(row.get('high')),
                'low': _safe_float(row.get('low')),
                'volume': _safe_float(row.get('volume')),
                'amount': _safe_float(row.get('amount')),
                'change_pct': _safe_float(row.get('change_pct')),
                'change': _safe_float(row.get('change')),
                'turnover_rate': _safe_float(row.get('turnover_rate')),
            }
            kline.append(entry)

        result = {
            'code': code,
            'period': period,
            'adjust': adjust,
            'data': kline,
        }

        set_cached(cache_key, result, ttl_seconds=300)
        return _success(result)

    except Exception as e:
        logger.warning("Failed to fetch K-line data for %s: %s, using mock", code, e)
        from services.mock_data import generate_kline
        kline = generate_kline(code)
        result = {'code': code, 'period': period, 'adjust': adjust, 'data': kline}
        set_cached(cache_key, result, ttl_seconds=30)
        return _success(result)


@stock_bp.route('/api/stock/<code>/realtime', methods=['GET'])
def realtime_quote(code):
    """Get real-time quote for a stock.

    Path params:
        code: Stock code
    """
    code = normalize_stock_code(code)
    market = get_market_from_code(code)

    cache_key = f'stock_realtime_{code}'
    cached = get_cached(cache_key, max_age_seconds=10)
    if cached is not None:
        return _success(cached)

    try:
        from services.stock_data import get_kline, get_stock_info
        # Use baostock for latest data
        df = get_kline(code, period='daily')
        info = get_stock_info(code)

        if df is None or df.empty:
            return _error(f"No data available for stock {code}")

        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        price = float(latest.get('close', 0))
        pre_close = float(prev.get('close', 0))

        result = {
            'code': code,
            'name': info.get('name', f'股票{code}'),
            'price': round(price, 2),
            'open': _safe_float(latest.get('open')),
            'high': _safe_float(latest.get('high')),
            'low': _safe_float(latest.get('low')),
            'pre_close': round(pre_close, 2),
            'change': round(price - pre_close, 2),
            'change_pct': _safe_float(latest.get('change_pct')),
            'volume': _safe_float(latest.get('volume')),
            'amount': _safe_float(latest.get('amount')),
            'turnover_rate': _safe_float(latest.get('turnover_rate')),
            'pe': 0, 'pb': 0, 'market_cap': 0, 'float_market_cap': 0,
            'amplitude': 0, 'volume_ratio': 0,
            'market': market,
            'timestamp': datetime.now().isoformat(),
        }

        set_cached(cache_key, result, ttl_seconds=30)
        return _success(result)

    except Exception as e:
        logger.warning("Failed to fetch realtime quote for %s: %s, using mock", code, e)
        from services.mock_data import generate_fundamental
        mock = generate_fundamental(code)
        result = {
            'code': code, 'name': mock['name'], 'price': mock.get('base', 20),
            'open': round(mock.get('base', 20) * 0.99, 2),
            'high': round(mock.get('base', 20) * 1.02, 2),
            'low': round(mock.get('base', 20) * 0.98, 2),
            'pre_close': round(mock.get('base', 20) * 0.995, 2),
            'change': round(mock.get('base', 20) * 0.01, 2),
            'change_pct': 1.0, 'volume': 500000, 'amount': 1e9,
            'turnover_rate': 2.5, 'pe': mock['pe_dynamic'], 'pb': mock['pb'],
            'market_cap': mock['market_cap'], 'float_market_cap': mock['float_market_cap'],
            'amplitude': 3.5, 'volume_ratio': 1.2, 'market': 'SZ',
            'timestamp': datetime.now().isoformat(),
        }
        set_cached(cache_key, result, ttl_seconds=10)
        return _success(result)


@stock_bp.route('/api/stock/<code>/indicators', methods=['GET'])
def stock_indicators(code):
    """Compute and return technical indicators for a stock.

    Returns MA(5,10,20,60,120,250), MACD, KDJ, RSI, BOLL.

    Path params:
        code: Stock code
    """
    code = normalize_stock_code(code)

    cache_key = f'stock_indicators_{code}'
    cached = get_cached(cache_key, max_age_seconds=300)
    if cached is not None:
        return _success(cached)

    try:
        from services.stock_data import get_kline
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=500)).strftime('%Y%m%d')

        df = get_kline(
            code=code,
            start_date=start_date,
            end_date=end_date,
            adjust='qfq',
        )

        if df is None or df.empty:
            return _error(f"No data found for stock {code}")

        # Baostock already returns English column names
        # Ensure date column exists
        if 'date' not in df.columns and '日期' in df.columns:
            df = df.rename(columns={'日期': 'date'})

        # Ensure numeric columns
        for col in ['open', 'close', 'high', 'low', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # Calculate all indicators
        df = calculate_all_indicators(df)

        # Get the latest indicators
        latest = df.iloc[-1] if len(df) > 0 else {}

        # Build MA data series
        ma_periods = [5, 10, 20, 60, 120, 250]
        ma_data = {}
        for p in ma_periods:
            col = f'MA{p}'
            if col in df.columns:
                # Return last 60 values for charting
                values = df[col].dropna().tail(60).tolist()
                ma_data[col] = [round(v, 2) if not np.isnan(v) else None
                                for v in values]

        # MACD data
        macd_data = {
            'DIF': _safe_float(latest.get('DIF')),
            'DEA': _safe_float(latest.get('DEA')),
            'MACD': _safe_float(latest.get('MACD')),
            'history': {
                'DIF': [round(v, 2) if not np.isnan(v) else None
                        for v in df['DIF'].dropna().tail(60).tolist()],
                'DEA': [round(v, 2) if not np.isnan(v) else None
                        for v in df['DEA'].dropna().tail(60).tolist()],
                'MACD': [round(v, 2) if not np.isnan(v) else None
                         for v in df['MACD'].dropna().tail(60).tolist()],
            } if 'DIF' in df.columns else {},
        }

        # KDJ data
        kdj_data = {
            'K': _safe_float(latest.get('K')),
            'D': _safe_float(latest.get('D')),
            'J': _safe_float(latest.get('J')),
            'history': {
                'K': [round(v, 2) if not np.isnan(v) else None
                      for v in df['K'].dropna().tail(60).tolist()],
                'D': [round(v, 2) if not np.isnan(v) else None
                      for v in df['D'].dropna().tail(60).tolist()],
                'J': [round(v, 2) if not np.isnan(v) else None
                      for v in df['J'].dropna().tail(60).tolist()],
            } if 'K' in df.columns else {},
        }

        # RSI data
        rsi_periods = [6, 12, 24]
        rsi_data = {}
        for p in rsi_periods:
            col = f'RSI{p}'
            rsi_data[col] = _safe_float(latest.get(col))
        rsi_data['history'] = {}
        for p in rsi_periods:
            col = f'RSI{p}'
            if col in df.columns:
                rsi_data['history'][col] = [
                    round(v, 2) if not np.isnan(v) else None
                    for v in df[col].dropna().tail(60).tolist()
                ]

        # BOLL data
        boll_data = {
            'UPPER': _safe_float(latest.get('BOLL_UPPER')),
            'MID': _safe_float(latest.get('BOLL_MID')),
            'LOWER': _safe_float(latest.get('BOLL_LOWER')),
            'history': {
                'UPPER': [round(v, 2) if not np.isnan(v) else None
                          for v in df['BOLL_UPPER'].dropna().tail(60).tolist()],
                'MID': [round(v, 2) if not np.isnan(v) else None
                        for v in df['BOLL_MID'].dropna().tail(60).tolist()],
                'LOWER': [round(v, 2) if not np.isnan(v) else None
                          for v in df['BOLL_LOWER'].dropna().tail(60).tolist()],
            } if 'BOLL_MID' in df.columns else {},
        }

        result = {
            'code': code,
            'MA': ma_data,
            'MACD': macd_data,
            'KDJ': kdj_data,
            'RSI': rsi_data,
            'BOLL': boll_data,
        }

        set_cached(cache_key, result, ttl_seconds=300)
        return _success(result)

    except Exception as e:
        logger.warning("Failed to calculate indicators for %s: %s, using mock", code, e)
        from services.mock_data import generate_kline
        mock_kline = generate_kline(code, days=500)
        df = pd.DataFrame(mock_kline)
        for col in ['open', 'close', 'high', 'low', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df = calculate_all_indicators(df)
        latest = df.iloc[-1] if len(df) > 0 else {}
        ma_data = {}
        for p in [5, 10, 20, 60, 120, 250]:
            col = f'MA{p}'
            if col in df.columns:
                ma_data[col] = [round(v, 2) if not np.isnan(v) else None for v in df[col].dropna().tail(60).tolist()]
        result = {
            'code': code,
            'MA': ma_data,
            'MACD': {'DIF': _safe_float(latest.get('DIF')), 'DEA': _safe_float(latest.get('DEA')), 'MACD': _safe_float(latest.get('MACD'))},
            'KDJ': {'K': _safe_float(latest.get('K')), 'D': _safe_float(latest.get('D')), 'J': _safe_float(latest.get('J'))},
            'RSI': {f'RSI{p}': _safe_float(latest.get(f'RSI{p}')) for p in [6, 12, 24]},
            'BOLL': {'UPPER': _safe_float(latest.get('BOLL_UPPER')), 'MID': _safe_float(latest.get('BOLL_MID')), 'LOWER': _safe_float(latest.get('BOLL_LOWER'))},
        }
        set_cached(cache_key, result, ttl_seconds=30)
        return _success(result)


@stock_bp.route('/api/stock/<code>/fundamental', methods=['GET'])
def stock_fundamental(code):
    """Get fundamental data for a stock.

    Returns PE, PB, market cap, revenue, and other fundamentals.

    Path params:
        code: Stock code
    """
    code = normalize_stock_code(code)

    cache_key = f'stock_fundamental_{code}'
    cached = get_cached(cache_key, max_age_seconds=600)
    if cached is not None:
        return _success(cached)

    try:
        import akshare as ak
        # Get individual stock info
        df = ak.stock_individual_info_em(symbol=code)

        if df is None or df.empty:
            return _error(f"No fundamental data found for stock {code}")

        # Build result from the info DataFrame
        result = {'code': code}
        info_dict = {}
        for _, row in df.iterrows():
            key = str(row.iloc[0]) if len(row) > 0 else ''
            value = row.iloc[1] if len(row) > 1 else ''
            info_dict[key] = value

        # Map known fields
        field_map = {
            '总市值': 'market_cap',
            '流通市值': 'float_market_cap',
            '行业': 'industry',
            '上市时间': 'listing_date',
            '股票代码': 'stock_code',
            '股票简称': 'name',
            '市盈率(动态)': 'pe_dynamic',
            '市净率': 'pb',
            '总股本': 'total_shares',
            '流通股': 'float_shares',
        }

        for cn_key, en_key in field_map.items():
            if cn_key in info_dict:
                result[en_key] = info_dict[cn_key]

        # Try to get financial data
        try:
            fin_df = ak.stock_financial_abstract_ths(symbol=code, indicator="按报告期")
            if fin_df is not None and not fin_df.empty:
                latest = fin_df.iloc[0]
                fin_data = {}
                for col in fin_df.columns:
                    val = latest.get(col)
                    if val is not None:
                        fin_data[str(col)] = str(val)
                result['financial_abstract'] = fin_data
        except Exception as fe:
            logger.debug("Could not fetch financial abstract for %s: %s", code, fe)

        set_cached(cache_key, result, ttl_seconds=30)
        return _success(result)

    except Exception as e:
        logger.warning("Failed to fetch fundamental data for %s: %s, using mock", code, e)
        from services.mock_data import generate_fundamental
        result = generate_fundamental(code)
        set_cached(cache_key, result, ttl_seconds=30)
        return _success(result)


@stock_bp.route('/api/stock/search', methods=['GET'])
def stock_search():
    """Search stocks by code or name.

    Query params:
        keyword: Search keyword (code or name).

    Returns:
        List of matching stocks with code and name.
    """
    keyword = request.args.get('keyword', '').strip()
    if not keyword:
        return _success([])

    cache_key = f'stock_search_{keyword}'
    cached = get_cached(cache_key, max_age_seconds=3600)
    if cached is not None:
        return _success(cached)

    try:
        from services.stock_data import _ensure_login
        import baostock as bs
        _ensure_login()

        # Search by code or name using baostock stock list
        rs = bs.query_stock_basic()
        items = []
        while rs.next():
            row = rs.get_row_data()
            # row: [code, code_name, ipoDate, outDate, type, status]
            bs_code = row[0]  # e.g., "sh.600519"
            name = row[1]
            code_num = bs_code.split('.')[-1] if '.' in bs_code else bs_code

            # Only include active stocks (status=1)
            if len(row) > 5 and row[5] != '1':
                continue
            # Only include actual stocks (type=1)
            if len(row) > 4 and row[4] != '1':
                continue

            if keyword.lower() in code_num or keyword in name:
                items.append({'code': code_num, 'name': name})
                if len(items) >= 20:
                    break

        set_cached(cache_key, items, ttl_seconds=3600)
        return _success(items)
    except Exception as e:
        logger.warning("Stock search failed for '%s': %s, using mock", keyword, e)

    # Fallback: search mock data
    from services.mock_data import MOCK_STOCKS
    items = [
        {'code': s['code'], 'name': s['name']}
        for s in MOCK_STOCKS
        if keyword in s['code'] or keyword in s['name']
    ]
    set_cached(cache_key, items, ttl_seconds=3600)
    return _success(items)


@stock_bp.route('/api/stock/<code>/intraday', methods=['GET'])
def intraday_data(code):
    """Get intraday (minute-level) data for a stock.

    Returns list of {time, price, volume} for today.
    """
    code = normalize_stock_code(code)
    cache_key = f'stock_intraday_{code}'
    cached = get_cached(cache_key, max_age_seconds=30)
    if cached is not None:
        return _success(cached)

    try:
        import akshare as ak
        df = ak.stock_zh_a_hist_min_em(symbol=code, period='1', adjust='')
        if df is not None and not df.empty:
            col_map = {'时间': 'time', '最新价': 'price', '成交量': 'volume'}
            available_cols = {k: v for k, v in col_map.items() if k in df.columns}
            df = df.rename(columns=available_cols)
            data = []
            for _, row in df.iterrows():
                data.append({
                    'time': str(row.get('time', '')),
                    'price': _safe_float(row.get('price')),
                    'volume': _safe_float(row.get('volume')),
                })
            set_cached(cache_key, data, ttl_seconds=30)
            return _success(data)
    except Exception as e:
        logger.warning("Intraday data failed for %s: %s, using mock", code, e)

    # Generate mock intraday data
    import random
    random.seed(hash(code))
    from services.mock_data import generate_kline
    mock_kline = generate_kline(code, days=1)
    base = mock_kline[0]['close'] if mock_kline else 50.0
    price = base
    intraday = []
    for h in range(9, 16):
        for m in range(0, 60, 5):
            if h == 11 and m >= 30:
                continue
            if h == 12:
                continue
            if h == 15 and m > 0:
                continue
            price = price * (1 + random.gauss(0, 0.002))
            intraday.append({
                'time': f'{h:02d}:{m:02d}',
                'price': round(price, 2),
                'volume': int(random.uniform(10000, 200000)),
            })
    set_cached(cache_key, intraday, ttl_seconds=30)
    return _success(intraday)
