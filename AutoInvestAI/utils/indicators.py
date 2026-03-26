# ============================================================
#  utils/indicators.py
#  Technical indicator calculations for AutoInvest AI
#  Developer: A. SHANMUGANAADHAN
# ============================================================

import pandas as pd
import numpy as np


def moving_average(data: pd.DataFrame, window: int = 20, column: str = 'Close') -> pd.Series:
    """
    Compute Simple Moving Average (SMA).

    Args:
        data    : DataFrame containing price data.
        window  : Rolling window period (default 20).
        column  : Price column to use (default 'Close').

    Returns:
        pd.Series of moving average values.
    """
    try:
        return data[column].rolling(window=window, min_periods=1).mean()
    except Exception:
        return pd.Series([None] * len(data))


def calculate_rsi(data: pd.DataFrame, period: int = 14, column: str = 'Close') -> pd.Series:
    """
    Compute Relative Strength Index (RSI) using Wilder's smoothing.

    Args:
        data   : DataFrame with price data.
        period : Lookback period (default 14).
        column : Price column (default 'Close').

    Returns:
        pd.Series of RSI values (0–100).
    """
    try:
        delta = data[column].diff()
        gain  = delta.clip(lower=0)
        loss  = -delta.clip(upper=0)

        avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

        rs  = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50)
    except Exception:
        return pd.Series([50.0] * len(data))


def detect_trend(data: pd.DataFrame, column: str = 'Close') -> str:
    """
    Detect the current price trend using MA20 and MA50.

    Returns one of:
        'UPTREND'   — Price above both MAs, MA20 above MA50
        'DOWNTREND' — Price below both MAs, MA20 below MA50
        'SIDEWAYS'  — Mixed signals
    """
    try:
        if len(data) < 20:
            return "INSUFFICIENT DATA"

        close  = data[column].iloc[-1]
        ma20   = data[column].rolling(20, min_periods=1).mean().iloc[-1]
        ma50   = data[column].rolling(50, min_periods=1).mean().iloc[-1] if len(data) >= 50 else ma20

        if close > ma20 and ma20 >= ma50:
            return "UPTREND"
        elif close < ma20 and ma20 <= ma50:
            return "DOWNTREND"
        else:
            return "SIDEWAYS"
    except Exception:
        return "UNKNOWN"


def calculate_macd(
    data: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    column: str = 'Close'
) -> pd.DataFrame | None:
    """
    Compute MACD, Signal line, and Histogram.

    Returns:
        DataFrame with columns: ['MACD', 'Signal', 'Histogram']
        or None if calculation fails.
    """
    try:
        if len(data) < slow:
            return None

        ema_fast   = data[column].ewm(span=fast,   adjust=False).mean()
        ema_slow   = data[column].ewm(span=slow,   adjust=False).mean()
        macd_line  = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram  = macd_line - signal_line

        return pd.DataFrame({
            'MACD':      macd_line,
            'Signal':    signal_line,
            'Histogram': histogram
        })
    except Exception:
        return None


def calculate_bollinger_bands(
    data: pd.DataFrame,
    window: int = 20,
    num_std: float = 2.0,
    column: str = 'Close'
) -> pd.DataFrame | None:
    """
    Compute Bollinger Bands.

    Returns:
        DataFrame with columns: ['Middle', 'Upper', 'Lower']
        or None if calculation fails.
    """
    try:
        if len(data) < window:
            return None

        middle = data[column].rolling(window, min_periods=1).mean()
        std    = data[column].rolling(window, min_periods=1).std()
        upper  = middle + (num_std * std)
        lower  = middle - (num_std * std)

        return pd.DataFrame({
            'Middle': middle,
            'Upper':  upper,
            'Lower':  lower
        })
    except Exception:
        return None


def calculate_atr(data: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Average True Range (ATR) — measures market volatility.

    Returns:
        pd.Series of ATR values.
    """
    try:
        high  = data['High']
        low   = data['Low']
        close = data['Close']

        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low  - close.shift()).abs()
        ], axis=1).max(axis=1)

        return tr.ewm(alpha=1 / period, adjust=False).mean()
    except Exception:
        return pd.Series([0.0] * len(data))


def calculate_stochastic(
    data: pd.DataFrame,
    k_period: int = 14,
    d_period: int = 3
) -> pd.DataFrame | None:
    """
    Stochastic Oscillator (%K and %D).

    Returns:
        DataFrame with ['%K', '%D'] or None.
    """
    try:
        low_min  = data['Low'].rolling(k_period).min()
        high_max = data['High'].rolling(k_period).max()
        k        = 100 * (data['Close'] - low_min) / (high_max - low_min)
        d        = k.rolling(d_period).mean()
        return pd.DataFrame({'%K': k, '%D': d})
    except Exception:
        return None


def calculate_ema(
    data: pd.DataFrame,
    span: int = 20,
    column: str = 'Close'
) -> pd.Series:
    """
    Exponential Moving Average (EMA).

    Returns:
        pd.Series of EMA values.
    """
    try:
        return data[column].ewm(span=span, adjust=False).mean()
    except Exception:
        return pd.Series([None] * len(data))