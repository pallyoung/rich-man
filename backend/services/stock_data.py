"""Stock data service using baostock as primary source.

Provides reliable Chinese stock market data without TLS fingerprinting issues.
Falls back to akshare+curl_cffi for data not available in baostock.
"""

import logging
import threading
from datetime import datetime, timedelta

import baostock as bs
import pandas as pd

logger = logging.getLogger(__name__)

# Thread-local storage for baostock login state
_local = threading.local()


def _ensure_login():
    """Ensure baostock is logged in (per-thread)."""
    if not getattr(_local, 'logged_in', False):
        lg = bs.login()
        if lg.error_code != '0':
            raise RuntimeError(f"baostock login failed: {lg.error_msg}")
        _local.logged_in = True


def _code_to_bs(code: str) -> str:
    """Convert stock code to baostock format (e.g., '600519' -> 'sh.600519')."""
    code = code.strip()
    if code.startswith(('sh.', 'sz.', 'bj.')):
        return code
    if code.startswith(('6', '9')):
        return f"sh.{code}"
    elif code.startswith(('0', '2', '3')):
        return f"sz.{code}"
    elif code.startswith(('4', '8')):
        return f"bj.{code}"
    return f"sz.{code}"


def _safe_float(val, default=0.0):
    """Safely convert value to float."""
    try:
        if val == '' or val is None:
            return default
        return round(float(val), 2)
    except (ValueError, TypeError):
        return default


def get_kline(code: str, start_date: str = '', end_date: str = '',
              period: str = 'daily', adjust: str = 'qfq') -> pd.DataFrame:
    """Get K-line data for a stock.

    Args:
        code: Stock code (e.g., '600519', '000001')
        start_date: Start date in YYYYMMDD format
        end_date: End date in YYYYMMDD format
        period: 'daily', 'weekly', 'monthly'
        adjust: 'qfq' (forward), 'hfq' (backward), '' (none)

    Returns:
        DataFrame with columns: date, open, high, low, close, volume, amount,
        change_pct, change, turnover_rate
    """
    _ensure_login()
    bs_code = _code_to_bs(code)

    freq_map = {'daily': 'd', 'weekly': 'w', 'monthly': 'm'}
    adjust_map = {'qfq': '2', 'hfq': '1', '': '3'}
    bs_freq = freq_map.get(period, 'd')
    bs_adjust = adjust_map.get(adjust, '2')

    if not start_date:
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')

    # Normalize date format
    start_date = start_date.replace('-', '')
    end_date = end_date.replace('-', '')
    if len(start_date) == 8:
        start_date = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
    if len(end_date) == 8:
        end_date = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"

    fields = "date,open,high,low,close,volume,amount,pctChg,turn"
    rs = bs.query_history_k_data_plus(
        bs_code, fields,
        start_date=start_date, end_date=end_date,
        frequency=bs_freq, adjustflag=bs_adjust
    )

    rows = []
    while rs.next():
        rows.append(rs.get_row_data())

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=['date', 'open', 'high', 'low', 'close',
                                      'volume', 'amount', 'change_pct', 'turnover_rate'])
    for col in ['open', 'high', 'low', 'close', 'volume', 'amount', 'change_pct', 'turnover_rate']:
        df[col] = pd.to_numeric(df[col], errors='coerce').round(2)

    df['change'] = df['close'].diff().round(2)
    df['date'] = df['date'].str.replace('-', '')

    return df


def get_index_kline(code: str, start_date: str = '', end_date: str = '') -> pd.DataFrame:
    """Get K-line data for an index."""
    _ensure_login()

    # Map common index codes
    index_map = {
        '000001': 'sh.000001', '399001': 'sz.399001',
        '399006': 'sz.399006', '000688': 'sh.000688',
    }
    bs_code = index_map.get(code, _code_to_bs(code))

    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')

    start_date = start_date.replace('-', '')
    end_date = end_date.replace('-', '')
    if len(start_date) == 8:
        start_date = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
    if len(end_date) == 8:
        end_date = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"

    fields = "date,open,high,low,close,volume,amount,pctChg"
    rs = bs.query_history_k_data_plus(
        bs_code, fields,
        start_date=start_date, end_date=end_date,
        frequency="d"
    )

    rows = []
    while rs.next():
        rows.append(rs.get_row_data())

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=['date', 'open', 'high', 'low', 'close',
                                      'volume', 'amount', 'change_pct'])
    for col in ['open', 'high', 'low', 'close', 'volume', 'amount', 'change_pct']:
        df[col] = pd.to_numeric(df[col], errors='coerce').round(2)

    return df


def get_market_overview() -> list:
    """Get latest data for major indices."""
    indices = [
        ('sh.000001', '000001', '上证指数'),
        ('sz.399001', '399001', '深证成指'),
        ('sz.399006', '399006', '创业板指'),
        ('sh.000688', '000688', '科创50'),
    ]

    _ensure_login()
    result = []
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')

    for bs_code, code, name in indices:
        try:
            rs = bs.query_history_k_data_plus(
                bs_code, "date,close,volume,amount,pctChg",
                start_date=start_date, end_date=end_date,
                frequency="d"
            )
            rows = []
            while rs.next():
                rows.append(rs.get_row_data())

            if rows:
                latest = rows[-1]
                prev_close = _safe_float(rows[-2][1]) if len(rows) > 1 else 0
                price = _safe_float(latest[1])
                change_pct = _safe_float(latest[4])
                change = round(price - prev_close, 2) if prev_close else 0

                result.append({
                    'code': code,
                    'name': name,
                    'price': price,
                    'change': change,
                    'change_pct': change_pct,
                    'volume': _safe_float(latest[2]),
                    'amount': _safe_float(latest[3]),
                })
        except Exception as e:
            logger.warning("Failed to fetch index %s: %s", code, e)

    return result


def get_stock_info(code: str) -> dict:
    """Get basic stock information."""
    _ensure_login()
    bs_code = _code_to_bs(code)

    rs = bs.query_stock_basic(code=bs_code)
    while rs.next():
        row = rs.get_row_data()
        return {
            'code': code,
            'name': row[1],
            'ipo_date': row[2],
            'out_date': row[3],
            'type': row[4],
            'status': row[5],
        }
    return {}


def get_industry_stocks() -> pd.DataFrame:
    """Get industry classification for stocks."""
    _ensure_login()
    rs = bs.query_stock_industry()

    rows = []
    while rs.next():
        rows.append(rs.get_row_data())

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=['updateDate', 'code', 'code_name', 'industry', 'industryClassification'])
    return df


def logout():
    """Logout from baostock."""
    if getattr(_local, 'logged_in', False):
        bs.logout()
        _local.logged_in = False
