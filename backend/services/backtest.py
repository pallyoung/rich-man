"""Backtesting engine for quantitative strategies."""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional

import numpy as np
import pandas as pd

from services.indicators import calculate_macd, calculate_ma, calculate_kdj

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """Represents a single trade."""
    date: str
    action: str  # "buy" or "sell"
    price: float
    shares: int
    amount: float
    commission: float


@dataclass
class BacktestResult:
    """Results from a backtest run."""
    equity_curve: List[Dict]
    trades: List[Dict]
    total_return: float = 0.0
    annual_return: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    win_rate: float = 0.0
    total_trades: int = 0
    initial_capital: float = 100000.0
    final_capital: float = 100000.0


class BacktestEngine:
    """Engine for running backtests on stock data."""

    def __init__(self):
        self.strategies = {
            'dual_ma': dual_ma_strategy,
            'macd': macd_strategy,
            'momentum': momentum_strategy,
            'turtle': turtle_strategy,
        }

    def run(self, df: pd.DataFrame, strategy: str,
            initial_capital: float = 100000,
            commission: float = 0.0003) -> BacktestResult:
        """Run a backtest on the given data with the specified strategy.

        Args:
            df: DataFrame with OHLCV data and date column.
            strategy: Strategy name ('dual_ma', 'macd', 'momentum').
            initial_capital: Starting capital in CNY.
            commission: Commission rate per trade (default 0.03%).

        Returns:
            BacktestResult with all metrics.
        """
        if strategy not in self.strategies:
            raise ValueError(
                f"Unknown strategy '{strategy}'. "
                f"Available: {list(self.strategies.keys())}"
            )

        df = df.copy()
        df = df.sort_values('date').reset_index(drop=True)

        # Generate signals using the strategy
        strategy_fn = self.strategies[strategy]
        signals = strategy_fn(df)

        # Simulate trading
        return self._simulate(df, signals, initial_capital, commission)

    def _simulate(self, df: pd.DataFrame, signals: pd.Series,
                  initial_capital: float, commission: float) -> BacktestResult:
        """Simulate trading based on signals.

        Args:
            df: OHLCV DataFrame.
            signals: Series with 1 (buy), -1 (sell), 0 (hold).
            initial_capital: Starting capital.
            commission: Commission rate.

        Returns:
            BacktestResult.
        """
        capital = initial_capital
        shares = 0
        trades = []
        equity_curve = []
        buy_price = 0.0

        for i in range(len(df)):
            row = df.iloc[i]
            signal = signals.iloc[i] if i < len(signals) else 0
            price = row['close']
            date_str = str(row.get('date', i))

            # Execute trades at close price
            if signal == 1 and shares == 0:
                # Buy signal: use all capital
                max_shares = int(capital / (price * (1 + commission)))
                # Round down to nearest 100 (Chinese market lot size)
                max_shares = (max_shares // 100) * 100
                if max_shares > 0:
                    cost = max_shares * price
                    comm = cost * commission
                    capital -= (cost + comm)
                    shares = max_shares
                    buy_price = price
                    trades.append({
                        'date': date_str,
                        'action': 'buy',
                        'price': round(price, 2),
                        'shares': shares,
                        'amount': round(cost, 2),
                        'commission': round(comm, 2),
                    })

            elif signal == -1 and shares > 0:
                # Sell signal: sell all shares
                revenue = shares * price
                comm = revenue * commission
                capital += (revenue - comm)
                trades.append({
                    'date': date_str,
                    'action': 'sell',
                    'price': round(price, 2),
                    'shares': shares,
                    'amount': round(revenue, 2),
                    'commission': round(comm, 2),
                })
                shares = 0

            # Record equity
            total_value = capital + shares * price
            equity_curve.append({
                'date': date_str,
                'equity': round(total_value, 2),
                'cash': round(capital, 2),
                'position_value': round(shares * price, 2),
            })

        # Calculate metrics
        return self._calculate_metrics(
            equity_curve, trades, initial_capital, capital, shares, df
        )

    def _calculate_metrics(self, equity_curve, trades, initial_capital,
                           final_cash, remaining_shares, df) -> BacktestResult:
        """Calculate performance metrics from backtest results."""
        if not equity_curve:
            return BacktestResult(
                equity_curve=[], trades=[],
                initial_capital=initial_capital,
                final_capital=initial_capital
            )

        equities = [e['equity'] for e in equity_curve]
        final_equity = equities[-1] if equities else initial_capital

        # Total return
        total_return = (final_equity - initial_capital) / initial_capital

        # Annualized return
        trading_days = len(equities)
        if trading_days > 1:
            annual_return = (1 + total_return) ** (252 / trading_days) - 1
        else:
            annual_return = 0.0

        # Maximum drawdown
        max_drawdown = 0.0
        peak = equities[0]
        for eq in equities:
            if eq > peak:
                peak = eq
            drawdown = (peak - eq) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        # Sharpe ratio (using daily returns)
        if len(equities) > 1:
            equity_series = pd.Series(equities)
            daily_returns = equity_series.pct_change().dropna()
            if daily_returns.std() > 0:
                sharpe_ratio = (
                    daily_returns.mean() / daily_returns.std()
                    * np.sqrt(252)
                )
            else:
                sharpe_ratio = 0.0
        else:
            sharpe_ratio = 0.0

        # Win rate
        total_trades = len([t for t in trades if t['action'] == 'sell'])
        winning_trades = 0
        i = 0
        while i < len(trades) - 1:
            if trades[i]['action'] == 'buy' and trades[i + 1]['action'] == 'sell':
                if trades[i + 1]['price'] > trades[i]['price']:
                    winning_trades += 1
                i += 2
            else:
                i += 1

        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0

        return BacktestResult(
            equity_curve=equity_curve,
            trades=trades,
            total_return=round(total_return, 4),
            annual_return=round(annual_return, 4),
            max_drawdown=round(max_drawdown, 4),
            sharpe_ratio=round(sharpe_ratio, 4),
            win_rate=round(win_rate, 4),
            total_trades=total_trades,
            initial_capital=initial_capital,
            final_capital=round(final_equity, 2),
        )


def dual_ma_strategy(df: pd.DataFrame, short: int = 5,
                     long: int = 20) -> pd.Series:
    """Dual Moving Average crossover strategy.

    Buy when short MA crosses above long MA (golden cross).
    Sell when short MA crosses below long MA (death cross).

    Args:
        df: DataFrame with 'close' column.
        short: Short MA period (default 5).
        long: Long MA period (default 20).

    Returns:
        Series of signals: 1 (buy), -1 (sell), 0 (hold).
    """
    ma_short = df['close'].rolling(window=short, min_periods=1).mean()
    ma_long = df['close'].rolling(window=long, min_periods=1).mean()

    signals = pd.Series(0, index=df.index)

    for i in range(1, len(df)):
        if pd.isna(ma_short.iloc[i]) or pd.isna(ma_long.iloc[i]):
            continue
        if pd.isna(ma_short.iloc[i - 1]) or pd.isna(ma_long.iloc[i - 1]):
            continue

        # Golden cross: short MA crosses above long MA
        if ma_short.iloc[i] > ma_long.iloc[i] and ma_short.iloc[i - 1] <= ma_long.iloc[i - 1]:
            signals.iloc[i] = 1
        # Death cross: short MA crosses below long MA
        elif ma_short.iloc[i] < ma_long.iloc[i] and ma_short.iloc[i - 1] >= ma_long.iloc[i - 1]:
            signals.iloc[i] = -1

    return signals


def macd_strategy(df: pd.DataFrame) -> pd.Series:
    """MACD crossover strategy.

    Buy when MACD line (DIF) crosses above signal line (DEA) - golden cross.
    Sell when MACD line crosses below signal line - death cross.

    Args:
        df: DataFrame with 'close' column.

    Returns:
        Series of signals: 1 (buy), -1 (sell), 0 (hold).
    """
    df_calc = calculate_macd(df)

    signals = pd.Series(0, index=df.index)

    for i in range(1, len(df_calc)):
        dif = df_calc['DIF'].iloc[i]
        dea = df_calc['DEA'].iloc[i]
        prev_dif = df_calc['DIF'].iloc[i - 1]
        prev_dea = df_calc['DEA'].iloc[i - 1]

        if pd.isna(dif) or pd.isna(dea) or pd.isna(prev_dif) or pd.isna(prev_dea):
            continue

        # Golden cross
        if dif > dea and prev_dif <= prev_dea:
            signals.iloc[i] = 1
        # Death cross
        elif dif < dea and prev_dif >= prev_dea:
            signals.iloc[i] = -1

    return signals


def momentum_strategy(df: pd.DataFrame, lookback: int = 20,
                      threshold: float = 0.03) -> pd.Series:
    """Momentum strategy.

    Buy when N-day return exceeds positive threshold.
    Sell when N-day return falls below negative threshold.

    Args:
        df: DataFrame with 'close' column.
        lookback: Lookback period in days (default 20).
        threshold: Return threshold for signals (default 3%).

    Returns:
        Series of signals: 1 (buy), -1 (sell), 0 (hold).
    """
    signals = pd.Series(0, index=df.index)

    # Calculate N-day returns
    returns = df['close'].pct_change(periods=lookback)

    for i in range(lookback, len(df)):
        ret = returns.iloc[i]
        if pd.isna(ret):
            continue

        if ret > threshold:
            signals.iloc[i] = 1
        elif ret < -threshold:
            signals.iloc[i] = -1

    return signals


def turtle_strategy(df: pd.DataFrame, entry_period: int = 20,
                    exit_period: int = 10) -> pd.Series:
    """Turtle trading strategy.

    Buy when price breaks above N-day high (Donchian channel breakout).
    Sell when price breaks below M-day low.

    Args:
        df: DataFrame with 'high', 'low', 'close' columns.
        entry_period: Lookback period for entry signal (default 20).
        exit_period: Lookback period for exit signal (default 10).

    Returns:
        Series of signals: 1 (buy), -1 (sell), 0 (hold).
    """
    signals = pd.Series(0, index=df.index)

    # Calculate Donchian channels
    upper_channel = df['high'].rolling(window=entry_period, min_periods=1).max()
    lower_channel = df['low'].rolling(window=exit_period, min_periods=1).min()

    for i in range(1, len(df)):
        if pd.isna(upper_channel.iloc[i - 1]) or pd.isna(lower_channel.iloc[i - 1]):
            continue

        # Buy: close breaks above 20-day high
        if df['close'].iloc[i] > upper_channel.iloc[i - 1]:
            signals.iloc[i] = 1
        # Sell: close breaks below 10-day low
        elif df['close'].iloc[i] < lower_channel.iloc[i - 1]:
            signals.iloc[i] = -1

    return signals
