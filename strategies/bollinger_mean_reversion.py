"""
Bollinger Band Mean Reversion Strategy

This is a REVERSAL strategy optimized for 1-minute binary options.
Unlike the breakout version, this trades AGAINST extreme moves,
expecting price to revert to the mean (Bollinger middle band).

Logic:
- CALL when price breaks BELOW lower band (expecting bounce back)
- PUT when price breaks ABOVE upper band (expecting pullback)

This aligns better with short-term binary options market behavior.

Author: QBot2 Trading System
Version: 2.0.0 - Mean Reversion
"""

from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


def calculate_bollinger_bands(
    candles: List[Dict],
    period: int = 14,
    deviation: float = 1.0
) -> Tuple[List[float], List[float], List[float]]:
    """
    Calculate Bollinger Bands (Upper, Middle, Lower)
    
    Args:
        candles: List of candle dictionaries with OHLC data
        period: Period for moving average calculation (default: 14)
        deviation: Standard deviation multiplier (default: 1.0)
    
    Returns:
        Tuple of (upper_band, middle_band, lower_band) lists
    """
    if len(candles) < period:
        logger.warning(f"Not enough candles for BB calculation. Need {period}, got {len(candles)}")
        return [], [], []
    
    closes = [float(c.get('close', 0)) for c in candles]
    
    upper_band = []
    middle_band = []
    lower_band = []
    
    for i in range(len(closes)):
        if i < period - 1:
            # Not enough data yet
            upper_band.append(0)
            middle_band.append(0)
            lower_band.append(0)
            continue
        
        # Calculate SMA (Simple Moving Average)
        sma = sum(closes[i - period + 1:i + 1]) / period
        
        # Calculate Standard Deviation
        variance = sum((x - sma) ** 2 for x in closes[i - period + 1:i + 1]) / period
        std_dev = variance ** 0.5
        
        # Calculate bands
        upper = sma + (deviation * std_dev)
        lower = sma - (deviation * std_dev)
        
        upper_band.append(upper)
        middle_band.append(sma)
        lower_band.append(lower)
    
    return upper_band, middle_band, lower_band


def compute_bollinger_mean_reversion_signal(
    candles: List[Dict],
    period: int = 20,
    deviation: float = 2.0
) -> Tuple[str, bool, str]:
    """
    Detect Bollinger Band mean reversion signals (OPTIMIZED FOR BINARY OPTIONS)
    
    MEAN REVERSION STRATEGY:
    - CALL when price breaks BELOW lower band (expecting bounce UP)
    - PUT when price breaks ABOVE upper band (expecting pullback DOWN)
    
    This is the OPPOSITE of breakout strategy and works better for:
    - 1-minute binary options
    - Mean-reverting markets
    - High-frequency trading
    
    Additional Filters:
    - Strong candle body (>40% of range)
    - Minimum distance from band (avoid marginal breaks)
    - Previous candle confirmation
    
    Args:
        candles: List of OHLC candle dictionaries (most recent last)
        period: Bollinger Band period (default: 20)
        deviation: Standard deviation multiplier (default: 2.0)
    
    Returns:
        Tuple of (signal, should_trade, reason)
    """
    # Need at least period + 2 candles (for BB calculation + prev + current)
    min_candles = period + 2
    if len(candles) < min_candles:
        return "HOLD", False, f"Not enough candles: need {min_candles}, got {len(candles)}"
    
    # Calculate Bollinger Bands
    upper_band, middle_band, lower_band = calculate_bollinger_bands(candles, period, deviation)
    
    if not upper_band or len(upper_band) < 2:
        return "HOLD", False, "Failed to calculate Bollinger Bands"
    
    # Get current and previous candle
    curr_candle = candles[-1]
    prev_candle = candles[-2]
    
    curr_open = float(curr_candle.get('open', 0))
    curr_close = float(curr_candle.get('close', 0))
    curr_high = float(curr_candle.get('max', 0))
    curr_low = float(curr_candle.get('min', 0))
    
    prev_close = float(prev_candle.get('close', 0))
    
    # Get BB values for current candle
    bb_upper = upper_band[-1]
    bb_middle = middle_band[-1]
    bb_lower = lower_band[-1]
    
    # Validate BB values
    if bb_upper == 0 or bb_lower == 0 or bb_middle == 0:
        return "HOLD", False, "Invalid Bollinger Band values"
    
    # Calculate candle body strength
    candle_range = curr_high - curr_low
    candle_body = abs(curr_close - curr_open)
    
    if candle_range == 0:
        return "HOLD", False, "Invalid candle: zero range"
    
    body_ratio = (candle_body / candle_range) * 100
    
    # Require decent body (>40% of range) - slightly lower than breakout
    if body_ratio < 40:
        return "HOLD", False, f"Weak candle body: {body_ratio:.1f}% (need >40%)"
    
    # Calculate band width for context
    band_width = ((bb_upper - bb_lower) / bb_middle) * 100
    
    # === CALL SIGNAL: Price Below Lower Band (Expecting Bounce UP) ===
    # Current candle closes below lower band AND is bearish
    oversold_condition = (
        curr_close < bb_lower and  # Currently below lower band
        curr_close < curr_open and  # Bearish candle (red)
        prev_close > bb_lower  # Previous was above (new break)
    )
    
    if oversold_condition:
        # Calculate how far below lower band
        distance_pct = ((bb_lower - curr_close) / bb_lower) * 100
        
        # Require minimum distance (0.01%) to avoid noise
        if distance_pct < 0.01:
            return "HOLD", False, f"Too close to lower band: {distance_pct:.3f}%"
        
        reason = (
            f"CALL (Mean Reversion): Oversold bounce expected | "
            f"Close={curr_close:.5f} < BB_Lower={bb_lower:.5f} | "
            f"Distance: {distance_pct:.3f}% | Body: {body_ratio:.1f}% | "
            f"Band Width: {band_width:.2f}%"
        )
        return "CALL", True, reason
    
    # === PUT SIGNAL: Price Above Upper Band (Expecting Pullback DOWN) ===
    # Current candle closes above upper band AND is bullish
    overbought_condition = (
        curr_close > bb_upper and  # Currently above upper band
        curr_close > curr_open and  # Bullish candle (green)
        prev_close < bb_upper  # Previous was below (new break)
    )
    
    if overbought_condition:
        # Calculate how far above upper band
        distance_pct = ((curr_close - bb_upper) / bb_upper) * 100
        
        # Require minimum distance (0.01%) to avoid noise
        if distance_pct < 0.01:
            return "HOLD", False, f"Too close to upper band: {distance_pct:.3f}%"
        
        reason = (
            f"PUT (Mean Reversion): Overbought pullback expected | "
            f"Close={curr_close:.5f} > BB_Upper={bb_upper:.5f} | "
            f"Distance: {distance_pct:.3f}% | Body: {body_ratio:.1f}% | "
            f"Band Width: {band_width:.2f}%"
        )
        return "PUT", True, reason
    
    # === NO SIGNAL ===
    if curr_close < bb_lower:
        position = "below lower band (but no reversal pattern)"
    elif curr_close > bb_upper:
        position = "above upper band (but no reversal pattern)"
    elif curr_close > bb_middle:
        position = "between middle and upper band"
    else:
        position = "between lower and middle band"
    
    reason = (
        f"No mean reversion signal | "
        f"Close={curr_close:.5f} | "
        f"BB=[{bb_lower:.5f}, {bb_middle:.5f}, {bb_upper:.5f}] | "
        f"Position: {position}"
    )
    
    return "HOLD", False, reason


if __name__ == "__main__":
    """
    Test the Mean Reversion strategy with sample data
    """
    # Sample test data (simulating oversold then bounce scenario)
    test_candles = [
        {'open': 1.1000, 'close': 1.0995, 'max': 1.1005, 'min': 1.0990},
        {'open': 1.0995, 'close': 1.0990, 'max': 1.1000, 'min': 1.0985},
        {'open': 1.0990, 'close': 1.0985, 'max': 1.0995, 'min': 1.0980},
        {'open': 1.0985, 'close': 1.0982, 'max': 1.0990, 'min': 1.0978},
        {'open': 1.0982, 'close': 1.0980, 'max': 1.0988, 'min': 1.0975},
        {'open': 1.0980, 'close': 1.0978, 'max': 1.0985, 'min': 1.0973},
        {'open': 1.0978, 'close': 1.0975, 'max': 1.0982, 'min': 1.0970},
        {'open': 1.0975, 'close': 1.0973, 'max': 1.0980, 'min': 1.0968},
        {'open': 1.0973, 'close': 1.0970, 'max': 1.0978, 'min': 1.0965},
        {'open': 1.0970, 'close': 1.0968, 'max': 1.0975, 'min': 1.0963},
        {'open': 1.0968, 'close': 1.0965, 'max': 1.0973, 'min': 1.0960},
        {'open': 1.0965, 'close': 1.0963, 'max': 1.0970, 'min': 1.0958},
        {'open': 1.0963, 'close': 1.0960, 'max': 1.0968, 'min': 1.0955},
        {'open': 1.0960, 'close': 1.0958, 'max': 1.0965, 'min': 1.0953},
        {'open': 1.0958, 'close': 1.0955, 'max': 1.0963, 'min': 1.0950},
        {'open': 1.0955, 'close': 1.0953, 'max': 1.0960, 'min': 1.0948},
        {'open': 1.0953, 'close': 1.0950, 'max': 1.0958, 'min': 1.0945},
        {'open': 1.0950, 'close': 1.0948, 'max': 1.0955, 'min': 1.0943},
        {'open': 1.0948, 'close': 1.0945, 'max': 1.0953, 'min': 1.0940},
        {'open': 1.0945, 'close': 1.0943, 'max': 1.0950, 'min': 1.0938},
        # Oversold candle: breaks below lower band (expecting bounce)
        {'open': 1.0943, 'close': 1.0935, 'max': 1.0945, 'min': 1.0930},
    ]
    
    print("=" * 80)
    print("BOLLINGER MEAN REVERSION STRATEGY TEST")
    print("=" * 80)
    
    # Test signal
    signal, should_trade, reason = compute_bollinger_mean_reversion_signal(
        test_candles, 
        period=20, 
        deviation=2.0
    )
    
    print(f"\n📊 Mean Reversion Signal:")
    print(f"   Signal: {signal}")
    print(f"   Should Trade: {should_trade}")
    print(f"   Reason: {reason}")
    
    # Show Bollinger Band values
    upper, middle, lower = calculate_bollinger_bands(test_candles, period=20, deviation=2.0)
    if upper:
        print(f"\n📈 Bollinger Bands (current):")
        print(f"   Upper Band: {upper[-1]:.5f}")
        print(f"   Middle Band: {middle[-1]:.5f}")
        print(f"   Lower Band: {lower[-1]:.5f}")
        print(f"   Current Close: {test_candles[-1]['close']:.5f}")
        print(f"   Distance from Lower: {((lower[-1] - test_candles[-1]['close']) / lower[-1] * 100):.3f}%")
    
    print("\n" + "=" * 80)
