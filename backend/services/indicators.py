"""Technical indicator calculation service using pandas/numpy.

All calculations are implemented without TA-Lib dependency.
Input DataFrame must have columns: [date, open, high, low, close, volume]
Output: DataFrame with indicator columns added.
"""

import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def calculate_ma(df: pd.DataFrame, periods: list = None) -> pd.DataFrame:
    """Calculate Moving Averages for given periods.

    Args:
        df: DataFrame with at least a 'close' column.
        periods: List of MA periods. Default: [5, 10, 20, 60, 120, 250].

    Returns:
        DataFrame with MA columns added (e.g., MA5, MA10, ...).
    """
    if periods is None:
        periods = [5, 10, 20, 60, 120, 250]

    df = df.copy()
    for period in periods:
        col_name = f'MA{period}'
        df[col_name] = df['close'].rolling(window=period, min_periods=1).mean()
        # Round to 2 decimal places
        df[col_name] = df[col_name].round(2)

    return df


def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26,
                   signal: int = 9) -> pd.DataFrame:
    """Calculate MACD (Moving Average Convergence Divergence).

    MACD Line = EMA(fast) - EMA(slow)
    Signal Line = EMA(MACD Line, signal)
    Histogram = MACD Line - Signal Line

    Args:
        df: DataFrame with at least a 'close' column.
        fast: Fast EMA period (default 12).
        slow: Slow EMA period (default 26).
        signal: Signal line EMA period (default 9).

    Returns:
        DataFrame with DIF, DEA, MACD columns added.
    """
    df = df.copy()

    # Calculate EMAs
    ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slow, adjust=False).mean()

    # DIF line (MACD line)
    df['DIF'] = (ema_fast - ema_slow).round(2)

    # DEA line (Signal line)
    df['DEA'] = df['DIF'].ewm(span=signal, adjust=False).mean().round(2)

    # MACD histogram (multiply by 2 per Chinese convention)
    df['MACD'] = ((df['DIF'] - df['DEA']) * 2).round(2)

    return df


def calculate_kdj(df: pd.DataFrame, n: int = 9, m1: int = 3,
                  m2: int = 3) -> pd.DataFrame:
    """Calculate KDJ indicator.

    RSV = (Close - Low_n) / (High_n - Low_n) * 100
    K = SMA(RSV, m1) using EWM-like smoothing
    D = SMA(K, m2)
    J = 3 * K - 2 * D

    Args:
        df: DataFrame with 'high', 'low', 'close' columns.
        n: RSV period (default 9).
        m1: K smoothing period (default 3).
        m2: D smoothing period (default 3).

    Returns:
        DataFrame with K, D, J columns added.
    """
    df = df.copy()

    # Calculate RSV (Raw Stochastic Value)
    low_n = df['low'].rolling(window=n, min_periods=1).min()
    high_n = df['high'].rolling(window=n, min_periods=1).max()

    # Avoid division by zero
    denominator = high_n - low_n
    denominator = denominator.replace(0, np.nan)

    rsv = ((df['close'] - low_n) / denominator * 100)
    rsv = rsv.fillna(50)  # Default to 50 when range is 0

    # Calculate K using iterative smoothing: K = (m1-1)/m1 * prev_K + 1/m1 * RSV
    k_values = np.zeros(len(df))
    d_values = np.zeros(len(df))

    k_values[0] = 50.0  # Initial value
    d_values[0] = 50.0  # Initial value

    rsv_arr = rsv.values
    for i in range(1, len(df)):
        k_values[i] = (m1 - 1) / m1 * k_values[i - 1] + 1 / m1 * rsv_arr[i]
        d_values[i] = (m2 - 1) / m2 * d_values[i - 1] + 1 / m2 * k_values[i]

    df['K'] = np.round(k_values, 2)
    df['D'] = np.round(d_values, 2)
    df['J'] = np.round(3 * df['K'] - 2 * df['D'], 2)

    return df


def calculate_rsi(df: pd.DataFrame, periods: list = None) -> pd.DataFrame:
    """Calculate RSI (Relative Strength Index).

    RSI = 100 - 100 / (1 + RS)
    RS = Average Gain / Average Loss

    Args:
        df: DataFrame with at least a 'close' column.
        periods: List of RSI periods. Default: [6, 12, 24].

    Returns:
        DataFrame with RSI columns added (e.g., RSI6, RSI12, RSI24).
    """
    if periods is None:
        periods = [6, 12, 24]

    df = df.copy()

    # Calculate price changes
    delta = df['close'].diff()

    for period in periods:
        col_name = f'RSI{period}'

        # Separate gains and losses
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)

        # Calculate average gain and loss using Wilder's smoothing (EWM)
        avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

        # Calculate RS and RSI
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))

        # Handle edge cases
        rsi = rsi.fillna(50)  # When avg_loss is 0, RSI = 100; when both 0, 50
        rsi = rsi.clip(0, 100)

        df[col_name] = rsi.round(2)

    return df


def calculate_boll(df: pd.DataFrame, n: int = 20, k: float = 2.0) -> pd.DataFrame:
    """Calculate Bollinger Bands.

    Middle Band = SMA(close, n)
    Upper Band = Middle Band + k * StdDev(close, n)
    Lower Band = Middle Band - k * StdDev(close, n)

    Args:
        df: DataFrame with at least a 'close' column.
        n: Period for moving average and standard deviation (default 20).
        k: Number of standard deviations (default 2).

    Returns:
        DataFrame with BOLL_UPPER, BOLL_MID, BOLL_LOWER columns added.
    """
    df = df.copy()

    # Middle band: simple moving average
    df['BOLL_MID'] = df['close'].rolling(window=n, min_periods=1).mean().round(2)

    # Standard deviation
    std = df['close'].rolling(window=n, min_periods=1).std()

    # Upper and lower bands
    df['BOLL_UPPER'] = (df['BOLL_MID'] + k * std).round(2)
    df['BOLL_LOWER'] = (df['BOLL_MID'] - k * std).round(2)

    return df


def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate all technical indicators and add them to the DataFrame.

    Args:
        df: DataFrame with columns [date, open, high, low, close, volume].

    Returns:
        DataFrame with all indicator columns added.
    """
    try:
        df = calculate_ma(df)
        df = calculate_macd(df)
        df = calculate_kdj(df)
        df = calculate_rsi(df)
        df = calculate_boll(df)
        logger.info("All indicators calculated for %d rows", len(df))
    except Exception as e:
        logger.error("Error calculating indicators: %s", e)
        raise

    return df
