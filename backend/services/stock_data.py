"""Stock data service using baostock as primary source.

Provides reliable Chinese stock market data without TLS fingerprinting issues.
Falls back to akshare+curl_cffi for data not available in baostock.

Key design: baostock uses a singleton TCP socket. All calls must be serialized
through a global lock to prevent data corruption from concurrent access.
"""

import logging
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta

import baostock as bs
import pandas as pd

logger = logging.getLogger(__name__)

# baostock uses a single global socket connection.
# A threading.Lock serializes all access so concurrent Flask request threads
# don't corrupt each other's reads/writes on the shared socket.
_lock = threading.Lock()
_logged_in = False


def _ensure_login():
    """Ensure baostock is logged in. **Caller must hold _lock.**"""
    global _logged_in
    if not _logged_in:
        lg = bs.login()
        if lg.error_code != '0':
            raise RuntimeError(f"baostock login failed: {lg.error_msg}")
        _logged_in = True


def reset_login():
    """Force a re-login on the next baostock call. **Caller must hold _lock.**"""
    global _logged_in
    _logged_in = False


@contextmanager
def baostock_session():
    """Thread-safe context manager for baostock operations.

    Acquires the global lock, ensures login, and yields.
    On connection-level errors the login flag is reset so the next call
    will re-establish the connection.
    """
    with _lock:
        _ensure_login()
        try:
            yield
        except Exception as e:
            # If the error is connection-related, force re-login next time.
            msg = str(e).lower()
            if any(kw in msg for kw in ('login', '网络', 'socket', 'recv',
                                         'utf-8', 'decompress', 'index out of range')):
                reset_login()
            raise


def bs_query(func, *args, **kwargs):
    """Execute a baostock query function in a thread-safe session with retry.

    Returns a list of row-data lists (each row is a list of strings).

    Usage::

        rows = bs_query(bs.query_history_k_data_plus, code, fields,
                        start_date=..., end_date=..., frequency="d")
    """
    max_retries = 3
    last_err = None
    for attempt in range(max_retries):
        try:
            with baostock_session():
                rs = func(*args, **kwargs)
                if rs is None:
                    raise RuntimeError("baostock returned None (socket may be dead)")
                rows = []
                while rs.next():
                    rows.append(rs.get_row_data())
                return rows
        except Exception as e:
            last_err = e
            msg = str(e).lower()
            retriable = any(kw in msg for kw in (
                'login', '网络', 'socket', 'recv', 'utf-8',
                'decompress', 'index out of range', 'none',
            ))
            if retriable and attempt < max_retries - 1:
                logger.warning("baostock call failed (attempt %d/%d): %s",
                               attempt + 1, max_retries, e)
                with _lock:
                    reset_login()
                continue
            raise


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


def _normalize_date(d: str) -> str:
    """Normalize a date string to YYYY-MM-DD format."""
    d = d.replace('-', '')
    if len(d) == 8:
        return f"{d[:4]}-{d[4:6]}-{d[6:]}"
    return d


def get_kline(code: str, start_date: str = '', end_date: str = '',
              period: str = 'daily', adjust: str = 'qfq') -> pd.DataFrame:
    """Get K-line data for a stock.

    Args:
        code: Stock code (e.g., '600519', '000001')
        start_date: Start date in YYYYMMDD or YYYY-MM-DD format
        end_date: End date in YYYYMMDD or YYYY-MM-DD format
        period: 'daily', 'weekly', 'monthly'
        adjust: 'qfq' (forward), 'hfq' (backward), '' (none)

    Returns:
        DataFrame with columns: date, open, high, low, close, volume, amount,
        change_pct, change, turnover_rate
    """
    bs_code = _code_to_bs(code)

    freq_map = {'daily': 'd', 'weekly': 'w', 'monthly': 'm'}
    adjust_map = {'qfq': '2', 'hfq': '1', '': '3'}
    bs_freq = freq_map.get(period, 'd')
    bs_adjust = adjust_map.get(adjust, '2')

    if not start_date:
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')

    start_date = _normalize_date(start_date)
    end_date = _normalize_date(end_date)

    fields = "date,open,high,low,close,volume,amount,pctChg,turn"
    rows = bs_query(
        bs.query_history_k_data_plus,
        bs_code, fields,
        start_date=start_date, end_date=end_date,
        frequency=bs_freq, adjustflag=bs_adjust,
    )

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
    index_map = {
        '000001': 'sh.000001', '399001': 'sz.399001',
        '399006': 'sz.399006', '000688': 'sh.000688',
    }
    bs_code = index_map.get(code, _code_to_bs(code))

    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')

    start_date = _normalize_date(start_date)
    end_date = _normalize_date(end_date)

    fields = "date,open,high,low,close,volume,amount,pctChg"
    rows = bs_query(
        bs.query_history_k_data_plus,
        bs_code, fields,
        start_date=start_date, end_date=end_date,
        frequency="d",
    )

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=['date', 'open', 'high', 'low', 'close',
                                      'volume', 'amount', 'change_pct'])
    for col in ['open', 'high', 'low', 'close', 'volume', 'amount', 'change_pct']:
        df[col] = pd.to_numeric(df[col], errors='coerce').round(2)

    return df


def get_market_overview() -> list:
    """Get latest data for major indices.

    Tries akshare real-time spot data first (intraday quotes from East Money),
    falls back to baostock end-of-day data.  Each item includes ``data_date``
    so the caller can tell whether the quote is from today or a prior day.
    """
    indices = [
        ('sh.000001', '000001', '上证指数'),
        ('sz.399001', '399001', '深证成指'),
        ('sz.399006', '399006', '创业板指'),
        ('sh.000688', '000688', '科创50'),
    ]

    # --- Strategy 1: akshare real-time spot data (intraday) ----------------
    result = _get_realtime_index_spot()

    # --- Strategy 2: baostock end-of-day data (fill gaps / full fallback) --
    expected_codes = {code for _, code, _ in indices}
    got_codes = {r['code'] for r in result}
    missing = expected_codes - got_codes
    if missing:
        eod = _get_baostock_index_eod(indices)
        # Add any indices we're still missing after baostock
        eod_got = {r['code'] for r in eod}
        for r in eod:
            if r['code'] in missing:
                result.append(r)
        # If nothing was fetched at all, pure baostock fallback
        if not result:
            result = eod

    return result


def _get_realtime_index_spot() -> list:
    """Try to fetch real-time index quotes via akshare (East Money).

    Returns a list of index dicts with ``data_date`` set to today, or an
    empty list if the request fails for any reason.
    """
    target_codes = {
        '000001': '上证指数',
        '399001': '深证成指',
        '399006': '创业板指',
        '000688': '科创50',
    }
    try:
        import akshare as ak
        import concurrent.futures

        def _fetch_spot(sym):
            return ak.stock_zh_index_spot_em(symbol=sym)

        frames = []
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        try:
            futures = {pool.submit(_fetch_spot, s): s
                       for s in ('上证系列指数', '深证系列指数')}
            for fut in concurrent.futures.as_completed(futures, timeout=8):
                try:
                    df = fut.result()
                    if df is not None and not df.empty:
                        frames.append(df)
                except Exception:
                    pass
        except concurrent.futures.TimeoutError:
            pass  # accept whatever we collected within the timeout
        finally:
            pool.shutdown(wait=False)

        if not frames:
            return []

        all_df = pd.concat(frames, ignore_index=True)

        result = []
        today_str = datetime.now().strftime('%Y-%m-%d')
        for _, row in all_df.iterrows():
            code = str(row.get('代码', '')).strip()
            if code not in target_codes:
                continue
            price = _safe_float(row.get('最新价'))
            change = _safe_float(row.get('涨跌额'))
            change_pct = _safe_float(row.get('涨跌幅'))
            result.append({
                'code': code,
                'name': target_codes[code],
                'price': price,
                'change': change,
                'change_pct': change_pct,
                'volume': _safe_float(row.get('成交量')),
                'amount': _safe_float(row.get('成交额')),
                'data_date': today_str,
            })

        if any(r['code'] == '000001' for r in result):
            logger.info("Market overview: using akshare real-time spot data")
            return result
        return []

    except Exception as e:
        logger.info("akshare real-time index spot unavailable: %s", e)
        return []


def _get_baostock_index_eod(indices: list) -> list:
    """Fetch end-of-day index data from baostock (historical / last close).

    Always includes ``data_date`` so the caller knows which trading day
    the quote belongs to — typically the *previous* trading day when the
    market is still open.
    """
    result = []
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')

    for bs_code, code, name in indices:
        try:
            rows = bs_query(
                bs.query_history_k_data_plus,
                bs_code, "date,close,volume,amount,pctChg",
                start_date=start_date, end_date=end_date,
                frequency="d",
            )

            if rows:
                latest = rows[-1]
                prev_close = _safe_float(rows[-2][1]) if len(rows) > 1 else 0
                price = _safe_float(latest[1])
                change_pct = _safe_float(latest[4])
                change = round(price - prev_close, 2) if prev_close else 0
                data_date = latest[0]  # e.g. '2026-05-28'

                result.append({
                    'code': code,
                    'name': name,
                    'price': price,
                    'change': change,
                    'change_pct': change_pct,
                    'volume': _safe_float(latest[2]),
                    'amount': _safe_float(latest[3]),
                    'data_date': data_date,
                })
            else:
                logger.warning("Index %s not available in baostock, skipping", code)
        except Exception as e:
            logger.warning("Failed to fetch index %s: %s", code, e)

    logger.info("Market overview: using baostock EOD data (last available trading day)")
    return result


def get_stock_info(code: str) -> dict:
    """Get basic stock information."""
    bs_code = _code_to_bs(code)
    rows = bs_query(bs.query_stock_basic, code=bs_code)
    if rows:
        row = rows[0]
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
    rows = bs_query(bs.query_stock_industry)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=['updateDate', 'code', 'code_name', 'industry', 'industryClassification'])
    return df


def logout():
    """Logout from baostock."""
    global _logged_in
    with _lock:
        if _logged_in:
            bs.logout()
            _logged_in = False
