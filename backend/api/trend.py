"""Trend analysis API blueprint.

Provides endpoints for buy/sell signal scanning,
multi-stock comparison, and sector rotation analysis.
"""

import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from flask import Blueprint, request, jsonify

from services.cache import get_cached, set_cached
from services.indicators import (
    calculate_macd, calculate_kdj, calculate_ma, calculate_rsi,
)
from utils.stock_utils import normalize_stock_code

logger = logging.getLogger(__name__)

trend_bp = Blueprint('trend', __name__)


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


def _fetch_stock_hist(code: str, days: int = 120) -> pd.DataFrame:
    """Fetch historical data for a stock.

    Args:
        code: 6-digit stock code.
        days: Number of calendar days to fetch.

    Returns:
        DataFrame with OHLCV data, or empty DataFrame on failure.
    """
    try:
        from services.stock_data import get_kline
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')

        df = get_kline(code, start_date=start_date, end_date=end_date, adjust='qfq')

        if df is None or df.empty:
            return pd.DataFrame()

        for col in ['open', 'close', 'high', 'low', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        return df
    except Exception as e:
        logger.warning("Failed to fetch history for %s: %s", code, e)
        return pd.DataFrame()


def _detect_macd_signals(df: pd.DataFrame) -> dict:
    """Detect MACD golden cross and death cross signals.

    Returns dict with signal info for the most recent data point.
    """
    df = calculate_macd(df)
    if len(df) < 2:
        return {'signal': 'none', 'description': 'Insufficient data'}

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    dif = latest['DIF']
    dea = latest['DEA']
    prev_dif = prev['DIF']
    prev_dea = prev['DEA']

    if pd.isna(dif) or pd.isna(dea) or pd.isna(prev_dif) or pd.isna(prev_dea):
        return {'signal': 'none', 'description': 'Insufficient data'}

    if dif > dea and prev_dif <= prev_dea:
        return {
            'signal': 'buy',
            'type': 'MACD',
            'description': 'MACD金叉 (DIF上穿DEA)',
            'DIF': round(dif, 2),
            'DEA': round(dea, 2),
            'MACD': round(latest['MACD'], 2),
        }
    elif dif < dea and prev_dif >= prev_dea:
        return {
            'signal': 'sell',
            'type': 'MACD',
            'description': 'MACD死叉 (DIF下穿DEA)',
            'DIF': round(dif, 2),
            'DEA': round(dea, 2),
            'MACD': round(latest['MACD'], 2),
        }

    return {
        'signal': 'none',
        'type': 'MACD',
        'DIF': round(dif, 2),
        'DEA': round(dea, 2),
        'MACD': round(latest['MACD'], 2),
    }


def _detect_kdj_signals(df: pd.DataFrame) -> dict:
    """Detect KDJ buy/sell signals.

    Buy: K crosses above D from below 20 (oversold zone).
    Sell: K crosses below D from above 80 (overbought zone).
    """
    df = calculate_kdj(df)
    if len(df) < 2:
        return {'signal': 'none', 'description': 'Insufficient data'}

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    k = latest['K']
    d = latest['D']
    j = latest['J']
    prev_k = prev['K']
    prev_d = prev['D']

    if pd.isna(k) or pd.isna(d) or pd.isna(prev_k) or pd.isna(prev_d):
        return {'signal': 'none', 'description': 'Insufficient data'}

    # Golden cross in oversold zone
    if k > d and prev_k <= prev_d and k < 30:
        return {
            'signal': 'buy',
            'type': 'KDJ',
            'description': f'KDJ金叉 (K={k:.1f}, D={d:.1f}, J={j:.1f})，超卖区域',
            'K': round(k, 2),
            'D': round(d, 2),
            'J': round(j, 2),
        }
    # Death cross in overbought zone
    elif k < d and prev_k >= prev_d and k > 70:
        return {
            'signal': 'sell',
            'type': 'KDJ',
            'description': f'KDJ死叉 (K={k:.1f}, D={d:.1f}, J={j:.1f})，超买区域',
            'K': round(k, 2),
            'D': round(d, 2),
            'J': round(j, 2),
        }

    return {
        'signal': 'none',
        'type': 'KDJ',
        'K': round(k, 2),
        'D': round(d, 2),
        'J': round(j, 2),
    }


def _detect_ma_signals(df: pd.DataFrame) -> dict:
    """Detect MA golden cross/death cross signals (5-day and 20-day MA)."""
    df = calculate_ma(df, periods=[5, 20])
    if len(df) < 2:
        return {'signal': 'none', 'description': 'Insufficient data'}

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    ma5 = latest['MA5']
    ma20 = latest['MA20']
    prev_ma5 = prev['MA5']
    prev_ma20 = prev['MA20']

    if pd.isna(ma5) or pd.isna(ma20) or pd.isna(prev_ma5) or pd.isna(prev_ma20):
        return {'signal': 'none', 'description': 'Insufficient data'}

    if ma5 > ma20 and prev_ma5 <= prev_ma20:
        return {
            'signal': 'buy',
            'type': 'MA',
            'description': 'MA5上穿MA20 (均线金叉)',
            'MA5': round(ma5, 2),
            'MA20': round(ma20, 2),
        }
    elif ma5 < ma20 and prev_ma5 >= prev_ma20:
        return {
            'signal': 'sell',
            'type': 'MA',
            'description': 'MA5下穿MA20 (均线死叉)',
            'MA5': round(ma5, 2),
            'MA20': round(ma20, 2),
        }

    return {
        'signal': 'none',
        'type': 'MA',
        'MA5': round(ma5, 2),
        'MA20': round(ma20, 2),
    }


def _detect_rsi_signals(df: pd.DataFrame) -> dict:
    """Detect RSI overbought/oversold signals."""
    df = calculate_rsi(df, periods=[6])
    if len(df) < 1:
        return {'signal': 'none', 'description': 'Insufficient data'}

    rsi6 = df.iloc[-1].get('RSI6', 50)
    if pd.isna(rsi6):
        return {'signal': 'none', 'description': 'Insufficient data'}

    if rsi6 < 20:
        return {
            'signal': 'buy',
            'type': 'RSI',
            'description': f'RSI6={rsi6:.1f}，极度超卖',
            'RSI6': round(rsi6, 2),
        }
    elif rsi6 > 80:
        return {
            'signal': 'sell',
            'type': 'RSI',
            'description': f'RSI6={rsi6:.1f}，极度超买',
            'RSI6': round(rsi6, 2),
        }

    return {
        'signal': 'none',
        'type': 'RSI',
        'RSI6': round(rsi6, 2),
    }


# Sample stocks for signal scanning (representative set)
SCAN_STOCKS = [
    '000001', '600036', '601318', '000858', '000333',
    '600519', '601166', '002415', '300750', '600030',
    '000651', '601888', '002304', '300059', '600276',
    '601398', '600900', '002714', '300760', '603259',
]



@trend_bp.route('/api/trend/compare', methods=['GET'])
def compare_trends():
    """Compare trends of multiple stocks.

    Query params:
        codes: Comma-separated stock codes (e.g., "000001,600036")
    """
    codes_param = request.args.get('codes', '')
    if not codes_param:
        return _error("Missing required parameter: codes")

    codes = [normalize_stock_code(c.strip()) for c in codes_param.split(',') if c.strip()]
    if len(codes) < 2:
        return _error("At least 2 stock codes are required")
    if len(codes) > 10:
        return _error("Maximum 10 stocks can be compared")

    cache_key = f'trend_compare_{"_".join(codes)}'
    cached = get_cached(cache_key, max_age_seconds=300)
    if cached is not None:
        return _success(cached)

    comparisons = []
    for code in codes:
        try:
            df = _fetch_stock_hist(code, days=365)
            if df.empty:
                comparisons.append({
                    'code': code,
                    'error': 'No data available',
                })
                continue

            df = calculate_ma(df, periods=[5, 20, 60])
            df = calculate_macd(df)
            df = calculate_kdj(df)
            df = calculate_rsi(df, periods=[6])

            # Calculate performance metrics
            close_series = df['close'].dropna()
            if len(close_series) < 2:
                comparisons.append({
                    'code': code,
                    'error': 'Insufficient data',
                })
                continue

            current_price = close_series.iloc[-1]

            # Period returns
            returns = {}
            for period_name, days in [('5d', 5), ('20d', 20), ('60d', 60),
                                       ('120d', 120), ('250d', 250)]:
                if len(close_series) >= days:
                    old_price = close_series.iloc[-days]
                    if old_price > 0:
                        returns[period_name] = round(
                            (current_price - old_price) / old_price * 100, 2
                        )

            # Volatility (20-day)
            if len(close_series) >= 20:
                daily_returns = close_series.pct_change().tail(20).dropna()
                volatility = round(daily_returns.std() * np.sqrt(252) * 100, 2)
            else:
                volatility = 0

            latest = df.iloc[-1]

            # Include price history for chart rendering
            dates = [str(d) for d in df['date'].tolist()]
            prices = [round(float(p), 2) for p in close_series.tolist()]

            comparisons.append({
                'code': code,
                'name': code,  # Frontend uses stock.name || stock.code
                'price': round(current_price, 2),
                'change_pct': _safe_float(df.iloc[-1].get('change_pct')),
                'returns': returns,
                'volatility': volatility,
                'dates': dates,
                'prices': prices,
                'MA5': _safe_float(latest.get('MA5')),
                'MA20': _safe_float(latest.get('MA20')),
                'MA60': _safe_float(latest.get('MA60')),
                'DIF': _safe_float(latest.get('DIF')),
                'DEA': _safe_float(latest.get('DEA')),
                'K': _safe_float(latest.get('K')),
                'D': _safe_float(latest.get('D')),
                'RSI6': _safe_float(latest.get('RSI6')),
                'trend': _determine_trend(latest),
            })

        except Exception as e:
            logger.error("Error comparing stock %s: %s", code, e)
            comparisons.append({
                'code': code,
                'error': str(e),
            })

    set_cached(cache_key, comparisons, ttl_seconds=30)
    return _success(comparisons)


def _determine_trend(row) -> str:
    """Determine the current trend from indicator values."""
    try:
        ma5 = row.get('MA5', 0)
        ma20 = row.get('MA20', 0)
        ma60 = row.get('MA60', 0)
        dif = row.get('DIF', 0)
        dea = row.get('DEA', 0)

        if pd.isna(ma5) or pd.isna(ma20) or pd.isna(ma60):
            return 'unknown'

        bullish = 0
        if ma5 > ma20:
            bullish += 1
        if ma20 > ma60:
            bullish += 1
        if not pd.isna(dif) and not pd.isna(dea) and dif > dea:
            bullish += 1

        if bullish >= 3:
            return 'strong_up'
        elif bullish == 2:
            return 'up'
        elif bullish == 1:
            return 'weak_up'
        elif bullish == 0:
            return 'down'
        return 'neutral'
    except Exception:
        return 'unknown'


@trend_bp.route('/api/trend/sector-rotation', methods=['GET'])
def sector_rotation():
    """Sector rotation analysis.

    Shows which sectors are gaining or losing momentum
    by comparing recent performance vs longer-term performance.
    """
    cache_key = 'trend_sector_rotation'
    cached = get_cached(cache_key, max_age_seconds=300)
    if cached is not None:
        return _success(cached)

    try:
        from services.stock_data import get_a_shares_realtime_batch, bs_query, _code_to_bs
        from services.mock_data import MOCK_STOCKS
        from collections import defaultdict

        # Get industry classification from baostock
        industry_rows = bs_query(bs.query_stock_industry)
        industry_map = {}
        for row in industry_rows:
            code_num = row[1].split('.')[-1] if '.' in row[1] else row[1]
            industry_name = row[3] if len(row) > 3 else ''
            if industry_name:
                industry_map[code_num] = industry_name

        industry_data = defaultdict(lambda: {'stocks': [], 'up': 0, 'down': 0, 'total_change': 0})

        # Strategy 1: akshare batch API
        df = get_a_shares_realtime_batch()
        if not df.empty and 'code' in df.columns:
            mock_codes = {s['code'] for s in MOCK_STOCKS}
            mock_info = {s['code']: s for s in MOCK_STOCKS}
            df_pool = df[df['code'].isin(mock_codes)]

            for _, row in df_pool.iterrows():
                code = str(row.get('code', ''))
                industry = industry_map.get(code, mock_info.get(code, {}).get('industry', '其他'))
                change_pct = _safe_float(row.get('change_pct'))
                industry_data[industry]['stocks'].append({
                    'code': code,
                    'name': str(row.get('name', mock_info.get(code, {}).get('name', ''))),
                    'change_pct': change_pct,
                })
                industry_data[industry]['total_change'] += change_pct
                if change_pct > 0:
                    industry_data[industry]['up'] += 1
                elif change_pct < 0:
                    industry_data[industry]['down'] += 1
        else:
            # Strategy 2: baostock fallback
            import baostock as bs
            from datetime import datetime, timedelta
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')

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
                        change_pct = _safe_float(latest[2])
                        industry_data[industry]['stocks'].append({'code': code, 'name': s['name'], 'change_pct': change_pct})
                        industry_data[industry]['total_change'] += change_pct
                        if change_pct > 0: industry_data[industry]['up'] += 1
                        elif change_pct < 0: industry_data[industry]['down'] += 1
                except Exception:
                    pass

        # Build a fake df-like structure for the existing logic below
        import pandas as pd
        rows_data = []
        for name, data in industry_data.items():
            if not data['stocks']:
                continue
            avg_change = round(data['total_change'] / len(data['stocks']), 2)
            rows_data.append({
                'name': name, 'code': '', 'change_pct': avg_change,
                'turnover_rate': 0, 'up_count': data['up'], 'down_count': data['down'],
            })
        df = pd.DataFrame(rows_data)

        sectors = []
        for _, row in df.iterrows():
            change_pct = _safe_float(row.get('change_pct'))
            turnover = _safe_float(row.get('turnover_rate'))
            up = int(_safe_float(row.get('up_count', 0)))
            down = int(_safe_float(row.get('down_count', 0)))

            # Determine momentum based on change and turnover
            if change_pct > 1 and turnover > 3:
                momentum = 'accelerating'
                direction = 'up'
            elif change_pct > 0:
                momentum = 'stable'
                direction = 'up'
            elif change_pct < -1 and turnover > 3:
                momentum = 'accelerating'
                direction = 'down'
            elif change_pct < 0:
                momentum = 'stable'
                direction = 'down'
            else:
                momentum = 'neutral'
                direction = 'flat'

            # Breadth: ratio of advancing to total stocks
            total = up + down
            breadth = round(up / total * 100, 1) if total > 0 else 50

            sectors.append({
                'name': str(row.get('name', '')),
                'code': str(row.get('code', '')),
                'change_pct': change_pct,
                'turnover_rate': turnover,
                'up_count': up,
                'down_count': down,
                'breadth': breadth,
                'momentum': momentum,
                'direction': direction,
            })

        # Sort: accelerating up sectors first, accelerating down last
        momentum_order = {
            'accelerating_up': 0,
            'stable_up': 1,
            'neutral': 2,
            'stable_down': 3,
            'accelerating_down': 4,
        }
        sectors.sort(
            key=lambda s: momentum_order.get(
                f"{s['momentum']}_{s['direction']}"
                if s['momentum'] != 'neutral' else 'neutral',
                2
            )
        )
        # Secondary sort by change_pct within same momentum
        sectors.sort(
            key=lambda s: (
                momentum_order.get(
                    f"{s['momentum']}_{s['direction']}"
                    if s['momentum'] != 'neutral' else 'neutral', 2
                ),
                -s['change_pct']
            )
        )

        # Add score field (0-100) for radar chart usage
        for s in sectors:
            # Score based on change_pct, breadth, and turnover
            change_score = min(max((s['change_pct'] + 5) / 10 * 100, 0), 100)
            breadth_score = s['breadth']
            turnover_score = min(s['turnover_rate'] / 5 * 100, 100)
            s['score'] = round(
                change_score * 0.5 + breadth_score * 0.3 + turnover_score * 0.2, 1
            )

        # Return flat array (frontend expects this)
        set_cached(cache_key, sectors, ttl_seconds=300)
        return _success(sectors)

    except Exception as e:
        logger.warning("Failed to analyze sector rotation: %s", e)
        return _error("暂无板块轮动数据")


def _build_rotation_summary(sectors: list) -> dict:
    """Build a summary of sector rotation."""
    up_sectors = [s for s in sectors if s['direction'] == 'up']
    down_sectors = [s for s in sectors if s['direction'] == 'down']
    accelerating_up = [s for s in sectors if s['momentum'] == 'accelerating' and s['direction'] == 'up']
    accelerating_down = [s for s in sectors if s['momentum'] == 'accelerating' and s['direction'] == 'down']

    return {
        'up_count': len(up_sectors),
        'down_count': len(down_sectors),
        'accelerating_up': [s['name'] for s in accelerating_up[:5]],
        'accelerating_down': [s['name'] for s in accelerating_down[:5]],
        'top_gainer': up_sectors[0]['name'] if up_sectors else None,
        'top_loser': down_sectors[-1]['name'] if down_sectors else None,
        'market_sentiment': 'bullish' if len(up_sectors) > len(down_sectors) * 1.5
        else 'bearish' if len(down_sectors) > len(up_sectors) * 1.5
        else 'neutral',
    }


@trend_bp.route('/api/trend/signals', methods=['GET'])
def trend_signals():
    """Get buy/sell trend signals for a basket of stocks.

    Returns a list of signal objects with standardized field names
    that match the frontend expectations.
    """
    cache_key = 'trend_signals'
    cached = get_cached(cache_key, max_age_seconds=120)
    if cached is not None:
        return _success(cached)

    try:
        from services.stock_data import get_kline
        from services.mock_data import MOCK_STOCKS
        from services.indicators import calculate_macd, calculate_kdj

        signals = []
        # Scan a sample of stocks for signals
        for s in MOCK_STOCKS[:20]:
            try:
                df = get_kline(s['code'], period='daily')
                if df is None or len(df) < 30:
                    continue

                df = calculate_macd(df)
                df = calculate_kdj(df)

                latest = df.iloc[-1]
                prev = df.iloc[-2]
                date_str = str(latest.get('date', ''))

                # MACD golden cross
                if (not pd.isna(latest.get('DIF')) and not pd.isna(latest.get('DEA'))
                    and not pd.isna(prev.get('DIF')) and not pd.isna(prev.get('DEA'))):
                    if latest['DIF'] > latest['DEA'] and prev['DIF'] <= prev['DEA']:
                        signals.append({
                            'stock_code': s['code'], 'stock_name': s['name'],
                            'signal_type': 'MACD金叉', 'signal_date': date_str,
                            'strength': 0.7, 'description': 'MACD线上穿信号线',
                            'direction': 'buy', 'price': round(float(latest['close']), 2),
                        })
                    elif latest['DIF'] < latest['DEA'] and prev['DIF'] >= prev['DEA']:
                        signals.append({
                            'stock_code': s['code'], 'stock_name': s['name'],
                            'signal_type': 'MACD死叉', 'signal_date': date_str,
                            'strength': 0.7, 'description': 'MACD线下穿信号线',
                            'direction': 'sell', 'price': round(float(latest['close']), 2),
                        })

                # KDJ golden cross
                if (not pd.isna(latest.get('K')) and not pd.isna(latest.get('D'))
                    and not pd.isna(prev.get('K')) and not pd.isna(prev.get('D'))):
                    if latest['K'] > latest['D'] and prev['K'] <= prev['D']:
                        signals.append({
                            'stock_code': s['code'], 'stock_name': s['name'],
                            'signal_type': 'KDJ金叉', 'signal_date': date_str,
                            'strength': 0.55, 'description': 'K线上穿D线',
                            'direction': 'buy', 'price': round(float(latest['close']), 2),
                        })
                    elif latest['K'] < latest['D'] and prev['K'] >= prev['D']:
                        signals.append({
                            'stock_code': s['code'], 'stock_name': s['name'],
                            'signal_type': 'KDJ死叉', 'signal_date': date_str,
                            'strength': 0.55, 'description': 'K线下穿D线',
                            'direction': 'sell', 'price': round(float(latest['close']), 2),
                        })
            except Exception:
                pass

        # Sort by date descending
        signals.sort(key=lambda x: x.get('signal_date', ''), reverse=True)
        set_cached(cache_key, signals[:20], ttl_seconds=120)
        return _success(signals[:20])
    except Exception as e:
        logger.warning("Failed to generate trend signals: %s", e)
        return _error("暂无趋势信号数据")


def _random_strength(signal_type):
    """Generate a strength value for a signal."""
    import random
    random.seed(hash(signal_type))
    return round(random.uniform(0.3, 0.9), 2)


@trend_bp.route('/api/trend/support-resistance/<code>', methods=['GET'])
def support_resistance(code):
    """Calculate support and resistance levels for a stock.

    Uses multiple methods:
    - Recent swing highs/lows
    - Moving averages (MA20, MA60)
    - Bollinger Bands
    - Volume-weighted levels

    Path params:
        code: Stock code

    Returns:
        Support and resistance levels with their sources.
    """
    code = normalize_stock_code(code)
    cache_key = f'trend_sr_{code}'
    cached = get_cached(cache_key, max_age_seconds=300)
    if cached is not None:
        return _success(cached)

    try:
        df = _fetch_stock_hist(code, days=120)
        if df.empty:
            return _error(f"No data for {code}")

        from services.indicators import calculate_ma, calculate_boll
        df = calculate_ma(df, periods=[20, 60])
        df = calculate_boll(df)

        latest = df.iloc[-1]
        current_price = float(latest.get('close', 0))

        supports = []
        resistances = []

        # MA-based levels
        for period in [20, 60]:
            ma_val = latest.get(f'MA{period}')
            if ma_val is not None and not pd.isna(ma_val):
                ma_val = round(float(ma_val), 2)
                if ma_val < current_price:
                    supports.append({'price': ma_val, 'source': f'MA{period}', 'strength': 'medium'})
                else:
                    resistances.append({'price': ma_val, 'source': f'MA{period}', 'strength': 'medium'})

        # Bollinger Band levels
        boll_upper = latest.get('BOLL_UPPER')
        boll_lower = latest.get('BOLL_LOWER')
        boll_mid = latest.get('BOLL_MID')

        if boll_upper is not None and not pd.isna(boll_upper):
            resistances.append({'price': round(float(boll_upper), 2), 'source': 'BOLL上轨', 'strength': 'strong'})
        if boll_mid is not None and not pd.isna(boll_mid):
            mid_val = round(float(boll_mid), 2)
            if mid_val < current_price:
                supports.append({'price': mid_val, 'source': 'BOLL中轨', 'strength': 'medium'})
            else:
                resistances.append({'price': mid_val, 'source': 'BOLL中轨', 'strength': 'medium'})
        if boll_lower is not None and not pd.isna(boll_lower):
            supports.append({'price': round(float(boll_lower), 2), 'source': 'BOLL下轨', 'strength': 'strong'})

        # Recent swing highs/lows (last 20 days)
        recent = df.tail(20)
        if len(recent) >= 5:
            highs = recent['high'].nlargest(3).tolist()
            lows = recent['low'].nsmallest(3).tolist()
            for h in highs:
                h = round(float(h), 2)
                if h > current_price * 1.005:
                    resistances.append({'price': h, 'source': '近期高点', 'strength': 'weak'})
            for l in lows:
                l = round(float(l), 2)
                if l < current_price * 0.995:
                    supports.append({'price': l, 'source': '近期低点', 'strength': 'weak'})

        # Deduplicate and sort
        supports = sorted(
            [s for s in supports if s['price'] > 0],
            key=lambda x: x['price'], reverse=True
        )[:5]
        resistances = sorted(
            [r for r in resistances if r['price'] > 0],
            key=lambda x: x['price']
        )[:5]

        result = {
            'code': code,
            'current_price': current_price,
            'supports': supports,
            'resistances': resistances,
        }

        set_cached(cache_key, result, ttl_seconds=300)
        return _success(result)

    except Exception as e:
        logger.warning("Failed to calculate support/resistance for %s: %s", code, e)
        return _error(f"Failed to calculate levels: {str(e)}")
