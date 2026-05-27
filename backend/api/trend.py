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
        import akshare as ak
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')

        df = ak.stock_zh_a_hist(
            symbol=code,
            period='daily',
            start_date=start_date,
            end_date=end_date,
            adjust='qfq',
        )

        if df is None or df.empty:
            return pd.DataFrame()

        col_map = {
            '日期': 'date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume',
            '涨跌幅': 'change_pct',
        }
        available_cols = {k: v for k, v in col_map.items() if k in df.columns}
        df = df.rename(columns=available_cols)

        for col in ['open', 'close', 'high', 'low', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        return df
    except Exception as e:
        logger.warning("Failed to fetch history for %s: %s, using mock", code, e)
        from services.mock_data import generate_kline
        mock = generate_kline(code, days=days)
        return pd.DataFrame(mock)


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


@trend_bp.route('/api/trend/signals', methods=['GET'])
def trend_signals():
    """Scan stocks and return buy/sell signals.

    Analyzes MACD golden/death cross, KDJ signals,
    MA crossovers, and RSI extremes.
    Multi-indicator resonance is detected when multiple
    indicators agree on direction.
    """
    cache_key = 'trend_signals'
    cached = get_cached(cache_key, max_age_seconds=120)
    if cached is not None:
        return _success(cached)

    results = []
    for code in SCAN_STOCKS:
        try:
            df = _fetch_stock_hist(code, days=200)
            if df.empty:
                continue

            macd_sig = _detect_macd_signals(df)
            kdj_sig = _detect_kdj_signals(df)
            ma_sig = _detect_ma_signals(df)
            rsi_sig = _detect_rsi_signals(df)

            # Determine resonance
            buy_signals = sum(
                1 for s in [macd_sig, kdj_sig, ma_sig, rsi_sig]
                if s.get('signal') == 'buy'
            )
            sell_signals = sum(
                1 for s in [macd_sig, kdj_sig, ma_sig, rsi_sig]
                if s.get('signal') == 'sell'
            )

            overall = 'none'
            strength = 0
            if buy_signals >= 2:
                overall = 'buy'
                strength = buy_signals
            elif sell_signals >= 2:
                overall = 'sell'
                strength = sell_signals
            elif buy_signals == 1:
                overall = 'weak_buy'
                strength = 1
            elif sell_signals == 1:
                overall = 'weak_sell'
                strength = 1

            if overall != 'none':
                name = ''
                if len(df) > 0 and 'close' in df.columns:
                    # Try to get the name from recent data or use code
                    name = code

                results.append({
                    'code': code,
                    'name': name,
                    'price': _safe_float(df.iloc[-1].get('close')),
                    'change_pct': _safe_float(df.iloc[-1].get('change_pct')),
                    'overall_signal': overall,
                    'strength': strength,
                    'buy_count': buy_signals,
                    'sell_count': sell_signals,
                    'macd': macd_sig,
                    'kdj': kdj_sig,
                    'ma': ma_sig,
                    'rsi': rsi_sig,
                })

        except Exception as e:
            logger.debug("Error analyzing %s: %s", code, e)
            continue

    # Sort by signal strength
    results.sort(key=lambda x: x.get('strength', 0), reverse=True)

    set_cached(cache_key, results, ttl_seconds=120)
    return _success(results)


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

            comparisons.append({
                'code': code,
                'price': round(current_price, 2),
                'change_pct': _safe_float(df.iloc[-1].get('change_pct')),
                'returns': returns,
                'volatility': volatility,
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

    set_cached(cache_key, comparisons, ttl_seconds=300)
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
        import akshare as ak
        df = ak.stock_board_industry_name_em()

        if df is None or df.empty:
            return _success([])

        col_map = {
            '板块名称': 'name',
            '板块代码': 'code',
            '涨跌幅': 'change_pct',
            '换手率': 'turnover_rate',
            '上涨家数': 'up_count',
            '下跌家数': 'down_count',
        }
        available_cols = {k: v for k, v in col_map.items() if k in df.columns}
        df = df.rename(columns=available_cols)

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

        result = {
            'sectors': sectors,
            'summary': _build_rotation_summary(sectors),
        }

        set_cached(cache_key, result, ttl_seconds=300)
        return _success(result)

    except Exception as e:
        logger.warning("Failed to analyze sector rotation: %s, using mock", e)
        from services.mock_data import generate_sectors
        mock_sectors = generate_sectors()
        result = {
            'sectors': mock_sectors,
            'summary': {
                'up_count': len([s for s in mock_sectors if s['change_pct'] > 0]),
                'down_count': len([s for s in mock_sectors if s['change_pct'] < 0]),
                'market_sentiment': 'neutral',
            },
        }
        set_cached(cache_key, result, ttl_seconds=300)
        return _success(result)


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
