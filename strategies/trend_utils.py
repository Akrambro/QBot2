"""
Shared utility functions for trading strategies

This module contains common functions used across multiple strategies
to avoid code duplication and maintain consistency.
"""

from typing import List, Dict


def get_trend_direction(candles: List[Dict], short_period: int = 5, long_period: int = 10) -> str:
    """
    Determine market trend using moving averages
    
    This function uses dual moving average crossover to identify market trends.
    The short MA represents recent price action while the long MA shows the
    overall trend direction.
    
    Args:
        candles: List of candle dictionaries with OHLC data
        short_period: Period for short-term moving average (default: 5, reduced from 10)
        long_period: Period for long-term moving average (default: 10, reduced from 20)
    
    Returns:
        "bullish" - Strong uptrend (short MA > long MA by 0.1%)
        "bearish" - Strong downtrend (short MA < long MA by 0.1%)
        "sideways" - No clear trend (within 0.1% threshold)
    
    Example:
        >>> candles = [{"close": "1.0850"}, {"close": "1.0860"}, ...]
        >>> trend = get_trend_direction(candles)
        >>> print(trend)  # "bullish", "bearish", or "sideways"
    
    Note:
        Reduced periods from 10/20 to 5/10 to work with limited candle data.
        Most strategies only fetch 10-15 candles, so this allows trend detection
        even with minimal historical data.
    """
    if len(candles) < long_period:
        # Not enough candles for full trend analysis - use simpler approach
        if len(candles) < 3:
            return "sideways"
        
        # Simple trend: compare last 3 candle closes
        recent_closes = [float(c["close"]) for c in candles[-3:]]
        if recent_closes[-1] > recent_closes[0] * 1.001:  # 0.1% higher
            return "bullish"
        elif recent_closes[-1] < recent_closes[0] * 0.999:  # 0.1% lower
            return "bearish"
        else:
            return "sideways"
    
    # Extract closing prices
    closes = [float(c["close"]) for c in candles[-long_period:]]
    
    # Calculate moving averages
    ma_short = sum(closes[-short_period:]) / short_period
    ma_long = sum(closes) / long_period
    
    # Determine trend with 0.1% threshold to filter noise
    threshold = 0.001  # 0.1% difference required
    
    if ma_short > ma_long * (1 + threshold):
        return "bullish"
    elif ma_short < ma_long * (1 - threshold):
        return "bearish"
    else:
        return "sideways"


def calculate_atr(candles: List[Dict], period: int = 14) -> float:
    """
    Calculate Average True Range (ATR) for volatility measurement
    
    ATR measures market volatility by calculating the average of true ranges.
    True Range = max(high - low, |high - prev_close|, |low - prev_close|)
    
    This is useful for:
    - Filtering high-volatility periods (news events)
    - Position sizing based on volatility
    - Setting appropriate stop-loss levels
    
    Args:
        candles: List of candle dictionaries with OHLC data
        period: Number of periods to calculate ATR over (default: 14)
    
    Returns:
        ATR value (higher = more volatile). Returns 0.0 if insufficient data.
    
    Example:
        >>> candles = [
        ...     {"high": "1.0860", "low": "1.0840", "close": "1.0850"},
        ...     {"high": "1.0870", "low": "1.0845", "close": "1.0865"},
        ...     ...
        ... ]
        >>> atr = calculate_atr(candles)
        >>> print(f"ATR: {atr:.5f}")  # ATR: 0.00125
    """
    if len(candles) < period + 1:
        return 0.0
    
    true_ranges = []
    for i in range(1, len(candles)):
        high = float(candles[i]["high"])
        low = float(candles[i]["low"])
        prev_close = float(candles[i-1]["close"])
        
        # Calculate True Range
        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close)
        )
        true_ranges.append(tr)
    
    # Calculate Average True Range
    if len(true_ranges) >= period:
        atr = sum(true_ranges[-period:]) / period
        return atr
    
    return 0.0
