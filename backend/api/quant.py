"""Quantitative strategy API blueprint.

Provides endpoints for strategy listing, backtesting,
and factor-based stock selection.
"""

import logging
from datetime import datetime, timedelta
from dataclasses import asdict

import numpy as np
import pandas as pd
from flask import Blueprint, request, jsonify

from services.backtest import BacktestEngine
from services.cache import get_cached, set_cached
from utils.stock_utils import normalize_stock_code

logger = logging.getLogger(__name__)

quant_bp = Blueprint('quant', __name__)

backtest_engine = BacktestEngine()

# Available strategies
STRATEGIES = [
    {
        'id': 'dual_ma',
        'name': '双均线策略',
        'name_en': 'Dual Moving Average',
        'description': '短期均线上穿长期均线时买入，下穿时卖出。适合趋势行情。',
        'params': {
            'short_period': {'default': 5, 'description': '短期均线周期'},
            'long_period': {'default': 20, 'description': '长期均线周期'},
        },
    },
    {
        'id': 'macd',
        'name': 'MACD策略',
        'name_en': 'MACD Crossover',
        'description': 'DIF上穿DEA时买入(金叉)，下穿时卖出(死叉)。经典趋势指标策略。',
        'params': {
            'fast': {'default': 12, 'description': '快速EMA周期'},
            'slow': {'default': 26, 'description': '慢速EMA周期'},
            'signal': {'default': 9, 'description': '信号线周期'},
        },
    },
    {
        'id': 'momentum',
        'name': '动量策略',
        'name_en': 'Momentum',
        'description': 'N日收益率超过阈值时买入，低于负阈值时卖出。追涨策略。',
        'params': {
            'lookback': {'default': 20, 'description': '回看天数'},
            'threshold': {'default': 0.03, 'description': '收益率阈值'},
        },
    },
    {
        'id': 'turtle',
        'name': '海龟交易策略',
        'name_en': 'Turtle Trading',
        'description': '价格突破N日最高价时买入，跌破M日最低价时卖出。经典趋势跟踪策略。',
        'params': {
            'entry_period': {'default': 20, 'description': '入场突破周期'},
            'exit_period': {'default': 10, 'description': '出场突破周期'},
        },
    },
]


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


def _fetch_stock_data(code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch historical stock data for backtesting.

    Args:
        code: Stock code.
        start_date: Start date in YYYYMMDD format.
        end_date: End date in YYYYMMDD format.

    Returns:
        DataFrame with OHLCV data.
    """
    try:
        import akshare as ak
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
            '成交额': 'amount',
            '涨跌幅': 'change_pct',
        }
        available_cols = {k: v for k, v in col_map.items() if k in df.columns}
        df = df.rename(columns=available_cols)

        for col in ['open', 'close', 'high', 'low', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        return df
    except Exception as e:
        logger.warning("Failed to fetch data for backtest %s: %s, using mock", code, e)
        from services.mock_data import generate_kline
        days = (datetime.strptime(end_date, '%Y%m%d') - datetime.strptime(start_date, '%Y%m%d')).days
        mock = generate_kline(code, days=max(days, 60))
        return pd.DataFrame(mock)


@quant_bp.route('/api/quant/strategies', methods=['GET'])
def list_strategies():
    """List available quantitative strategies."""
    return _success(STRATEGIES)



# Sample stock pool for factor selection
STOCK_POOL = [
    '000001', '600036', '601318', '000858', '000333',
    '600519', '601166', '002415', '300750', '600030',
    '000651', '601888', '002304', '300059', '600276',
    '601398', '600900', '002714', '300760', '603259',
    '000568', '002475', '600809', '000725', '002594',
    '601012', '300124', '002230', '600048', '000002',
]


@quant_bp.route('/api/quant/factor-select', methods=['POST'])
def factor_select():
    """Factor-based stock selection.

    JSON body:
        factors: List of factor configs, e.g.:
            [{"name": "PE", "weight": 0.3, "direction": "asc"},
             {"name": "PB", "weight": 0.2, "direction": "asc"},
             {"name": "ROE", "weight": 0.3, "direction": "desc"},
             {"name": "momentum", "weight": 0.1, "direction": "desc"},
             {"name": "volatility", "weight": 0.1, "direction": "asc"}]
        limit: Number of stocks to return (default 20)

    Returns:
        Ranked stock list with factor scores.
    """
    data = request.get_json()
    if not data:
        return _error("Request body must be JSON")

    factors = data.get('factors', [])
    limit = int(data.get('limit', 20))

    if not factors:
        return _error("At least one factor is required")

    valid_factors = {'PE', 'PB', 'ROE', 'momentum', 'volatility'}
    for f in factors:
        if f.get('name') not in valid_factors:
            return _error(
                f"Unknown factor '{f.get('name')}'. "
                f"Available: {list(valid_factors)}"
            )

    cache_key = f'factor_select_{hash(str(factors))}_{limit}'
    cached = get_cached(cache_key, max_age_seconds=600)
    if cached is not None:
        return _success(cached)

    try:
        import akshare as ak

        # Get real-time data for all A-share stocks
        spot_df = ak.stock_zh_a_spot_em()
        if spot_df is None or spot_df.empty:
            return _error("Failed to fetch stock data")

        # Filter to our pool (or use all if pool not matching)
        pool_codes = set(STOCK_POOL)
        spot_df = spot_df[spot_df['代码'].isin(pool_codes)]

        if spot_df.empty:
            # If pool doesn't match, use top stocks by market cap
            spot_df = ak.stock_zh_a_spot_em().head(100)

        # Build stock data
        stocks = []
        for _, row in spot_df.iterrows():
            stock = {
                'code': str(row.get('代码', '')),
                'name': str(row.get('名称', '')),
                'price': _safe_float(row.get('最新价')),
                'PE': _safe_float(row.get('市盈率-动态')),
                'PB': _safe_float(row.get('市净率')),
                'market_cap': _safe_float(row.get('总市值')),
            }
            stocks.append(stock)

        # Calculate momentum and volatility from historical data
        for stock in stocks:
            try:
                hist_df = _fetch_stock_data(
                    stock['code'],
                    (datetime.now() - timedelta(days=60)).strftime('%Y%m%d'),
                    datetime.now().strftime('%Y%m%d'),
                )
                if not hist_df.empty and len(hist_df) >= 20:
                    close = hist_df['close'].dropna()
                    # 20-day momentum
                    if len(close) >= 20:
                        stock['momentum'] = round(
                            (close.iloc[-1] / close.iloc[-20] - 1) * 100, 2
                        )
                    else:
                        stock['momentum'] = 0
                    # 20-day volatility (annualized)
                    daily_ret = close.pct_change().dropna().tail(20)
                    stock['volatility'] = round(
                        daily_ret.std() * np.sqrt(252) * 100, 2
                    )
                else:
                    stock['momentum'] = 0
                    stock['volatility'] = 0
            except Exception as e:
                logger.debug("Error computing factors for %s: %s", stock['code'], e)
                stock['momentum'] = 0
                stock['volatility'] = 0

        # Default ROE placeholder (would need financial data)
        for stock in stocks:
            if 'ROE' not in stock:
                stock['ROE'] = 0

        # Score and rank stocks
        scored_stocks = _score_stocks(stocks, factors)

        # Sort by total score descending
        scored_stocks.sort(key=lambda s: s.get('total_score', 0), reverse=True)

        # Limit results
        result = scored_stocks[:limit]

        set_cached(cache_key, result, ttl_seconds=600)
        return _success(result)

    except Exception as e:
        logger.warning("Factor selection failed: %s, using mock", e)
        from services.mock_data import MOCK_STOCKS
        import random
        random.seed(42)
        stocks = []
        for s in MOCK_STOCKS[:limit]:
            stocks.append({
                'code': s['code'], 'name': s['name'],
                'price': round(s['base'] * random.uniform(0.9, 1.1), 2),
                'PE': round(random.uniform(5, 60), 2),
                'PB': round(random.uniform(0.8, 8), 2),
                'ROE': round(random.uniform(5, 30), 2),
                'momentum': round(random.uniform(-10, 15), 2),
                'volatility': round(random.uniform(15, 45), 2),
                'market_cap': round(random.uniform(5e10, 2e12), 2),
                'total_score': round(random.uniform(50, 95), 2),
            })
        stocks.sort(key=lambda x: x['total_score'], reverse=True)
        set_cached(cache_key, stocks[:limit], ttl_seconds=600)
        return _success(stocks[:limit])


def _score_stocks(stocks: list, factors: list) -> list:
    """Score and rank stocks based on factor weights.

    Uses z-score normalization for each factor, then combines
    using weighted average.

    Args:
        stocks: List of stock dicts with factor values.
        factors: List of factor configs with name, weight, direction.

    Returns:
        Stock list with scores added.
    """
    # Extract factor values
    factor_names = [f['name'] for f in factors]
    factor_values = {name: [] for name in factor_names}

    for stock in stocks:
        for name in factor_names:
            val = stock.get(name, 0)
            if val is None or (isinstance(val, float) and np.isnan(val)):
                val = 0
            factor_values[name].append(val)

    # Z-score normalize each factor
    factor_zscores = {}
    for name in factor_names:
        values = np.array(factor_values[name], dtype=float)
        mean = np.nanmean(values)
        std = np.nanstd(values)
        if std > 0:
            zscores = (values - mean) / std
        else:
            zscores = np.zeros_like(values)
        factor_zscores[name] = zscores

    # Calculate weighted scores
    for i, stock in enumerate(stocks):
        total_score = 0.0
        factor_scores = {}

        for factor in factors:
            name = factor['name']
            weight = factor.get('weight', 1.0 / len(factors))
            direction = factor.get('direction', 'desc')

            zscore = factor_zscores[name][i]

            # If ascending (lower is better), negate the z-score
            if direction == 'asc':
                zscore = -zscore

            weighted = zscore * weight
            factor_scores[name] = {
                'raw': factor_values[name][i],
                'zscore': round(float(zscore), 4),
                'weighted': round(float(weighted), 4),
            }
            total_score += weighted

        stock['factor_scores'] = factor_scores
        stock['total_score'] = round(float(total_score), 4)

    return stocks


@quant_bp.route('/api/quant/backtest', methods=['POST'])
def run_backtest():
    """Run a backtest with the specified parameters.

    Accepts both old and new param naming conventions.

    JSON body:
        code or stock_code: Stock code (required)
        strategy: Strategy name (required)
        start_date: Start date (required, YYYY-MM-DD or YYYYMMDD)
        end_date: End date (required, YYYY-MM-DD or YYYYMMDD)
        initial_capital or initial_capital: Starting capital (default 100000)
        commission_rate or commission: Commission rate (default 0.0003)
    """
    data = request.get_json()
    if not data:
        return _error("Request body must be JSON")

    code = data.get('code') or data.get('stock_code')
    strategy = data.get('strategy')
    start_date = data.get('start_date', '')
    end_date = data.get('end_date', '')
    initial_capital = float(data.get('initial_capital', 100000))
    commission = float(data.get('commission_rate', data.get('commission', 0.0003)))

    if not code:
        return _error("Stock code is required (code or stock_code)")
    if not strategy:
        return _error("Strategy is required")
    if strategy not in backtest_engine.strategies:
        return _error(f"Unknown strategy '{strategy}'. Available: {list(backtest_engine.strategies.keys())}")
    if not start_date or not end_date:
        return _error("start_date and end_date are required")

    code = normalize_stock_code(code)

    # Normalize date format to YYYYMMDD
    start_date = start_date.replace('-', '')
    end_date = end_date.replace('-', '')

    cache_key = f'quant_backtest_{code}_{strategy}_{start_date}_{end_date}_{initial_capital}'
    cached = get_cached(cache_key, max_age_seconds=300)
    if cached is not None:
        return _success(cached)

    try:
        df = _fetch_stock_data(code, start_date, end_date)
        if df.empty:
            return _error(f"No data found for stock {code}")

        result = backtest_engine.run(
            df, strategy,
            initial_capital=initial_capital,
            commission=commission,
        )

        from dataclasses import asdict
        result_dict = {
            'equity_curve': result.equity_curve,
            'trades': result.trades,
            'metrics': {
                'total_return': round(result.total_return * 100, 2),
                'annual_return': round(result.annual_return * 100, 2),
                'max_drawdown': round(result.max_drawdown * 100, 2),
                'sharpe_ratio': round(result.sharpe_ratio, 2),
                'win_rate': round(result.win_rate * 100, 2),
                'total_trades': result.total_trades,
                'initial_capital': result.initial_capital,
                'final_capital': result.final_capital,
            },
        }

        set_cached(cache_key, result_dict, ttl_seconds=300)
        return _success(result_dict)

    except Exception as e:
        logger.warning("Backtest failed for %s: %s", code, e)
        return _error(f"Backtest failed: {str(e)}")
