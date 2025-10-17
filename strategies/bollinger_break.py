"""
Bollinger Band Breakout Strategy

Logic:
- Calculate Bollinger Bands with period 14 and deviation 1
- CALL signal: When candle opens below upper band and closes completely above it
- PUT signal: When candle opens above lower band and closes completely below it

Author: QBot2 Trading System
Version: 1.0.0
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


def compute_bollinger_break_signal(
    candles: List[Dict],
    period: int = 14,
    deviation: float = 1.0
) -> Tuple[str, bool, str]:
    """
    Detect Bollinger Band breakout signals
    
    CALL Signal:
    - Candle opens below upper band
    - Candle closes completely above upper band
    
    PUT Signal:
    - Candle opens above lower band
    - Candle closes completely below lower band
    
    Args:
        candles: List of OHLC candle dictionaries (most recent last)
        period: Bollinger Band period (default: 14)
        deviation: Standard deviation multiplier (default: 1.0)
    
    Returns:
        Tuple of (signal, should_trade, reason)
        - signal: "CALL", "PUT", or "HOLD"
        - should_trade: Boolean indicating if trade should be placed
        - reason: Explanation of the decision
    """
    # Need at least period + 1 candles (for BB calculation + current candle)
    min_candles = period + 1
    if len(candles) < min_candles:
        return "HOLD", False, f"Not enough candles: need {min_candles}, got {len(candles)}"
    
    # Calculate Bollinger Bands
    upper_band, middle_band, lower_band = calculate_bollinger_bands(candles, period, deviation)
    
    if not upper_band or len(upper_band) < 2:
        return "HOLD", False, "Failed to calculate Bollinger Bands"
    
    # Get the last completed candle (most recent)
    last_candle = candles[-1]
    candle_open = float(last_candle.get('open', 0))
    candle_close = float(last_candle.get('close', 0))
    candle_high = float(last_candle.get('max', 0))
    candle_low = float(last_candle.get('min', 0))
    
    # Get BB values for the last candle
    bb_upper = upper_band[-1]
    bb_middle = middle_band[-1]
    bb_lower = lower_band[-1]
    
    # Validate BB values
    if bb_upper == 0 or bb_lower == 0:
        return "HOLD", False, "Invalid Bollinger Band values"
    
    # === CALL SIGNAL (More Aggressive Detection) ===
    # Original: Candle opens below AND closes above upper band
    # Enhanced: Also detect if candle is TOUCHING/BREAKING the upper band
    # This catches breakouts earlier for better entry timing
    
    # Scenario 1: Classic breakout (opens below, closes above)
    classic_call_breakout = candle_open < bb_upper and candle_close > bb_upper
    
    # Scenario 2: Strong bullish candle that closes near/above upper band
    # (Catches momentum before full breakout completion)
    aggressive_call = (
        candle_close > candle_open and  # Bullish candle
        candle_close >= bb_upper * 0.9995 and  # Close at or very near upper band
        candle_high > bb_upper  # High touched/broke upper band
    )
    
    if classic_call_breakout or aggressive_call:
        # Determine detection mode
        detection_mode = "Classic" if classic_call_breakout else "Aggressive"
        
        # Calculate breakout strength
        breakout_strength = ((candle_close - bb_upper) / bb_upper) * 100 if candle_close > bb_upper else 0
        
        reason = (
            f"CALL ({detection_mode}): Bollinger upside breakout | "
            f"Open={candle_open:.5f}, Close={candle_close:.5f}, High={candle_high:.5f} | "
            f"BB_Upper={bb_upper:.5f} | Strength: {breakout_strength:.3f}%"
        )
        return "CALL", True, reason
    
    # === PUT SIGNAL (More Aggressive Detection) ===
    # Original: Candle opens above AND closes below lower band
    # Enhanced: Also detect if candle is TOUCHING/BREAKING the lower band
    
    # Scenario 1: Classic breakout (opens above, closes below)
    classic_put_breakout = candle_open > bb_lower and candle_close < bb_lower
    
    # Scenario 2: Strong bearish candle that closes near/below lower band
    # (Catches momentum before full breakout completion)
    aggressive_put = (
        candle_close < candle_open and  # Bearish candle
        candle_close <= bb_lower * 1.0005 and  # Close at or very near lower band
        candle_low < bb_lower  # Low touched/broke lower band
    )
    
    if classic_put_breakout or aggressive_put:
        # Determine detection mode
        detection_mode = "Classic" if classic_put_breakout else "Aggressive"
        
        # Calculate breakout strength
        breakout_strength = ((bb_lower - candle_close) / bb_lower) * 100 if candle_close < bb_lower else 0
        
        reason = (
            f"PUT ({detection_mode}): Bollinger downside breakout | "
            f"Open={candle_open:.5f}, Close={candle_close:.5f}, Low={candle_low:.5f} | "
            f"BB_Lower={bb_lower:.5f} | Strength: {breakout_strength:.3f}%"
        )
        return "PUT", True, reason
    
    # === NO SIGNAL ===
    # Check where price is relative to bands
    if candle_close > bb_upper:
        position = "above upper band (no breakout)"
    elif candle_close < bb_lower:
        position = "below lower band (no breakout)"
    elif candle_close > bb_middle:
        position = "between middle and upper band"
    else:
        position = "between lower and middle band"
    
    reason = (
        f"No breakout detected | "
        f"Close={candle_close:.5f}, "
        f"BB Range=[{bb_lower:.5f}, {bb_middle:.5f}, {bb_upper:.5f}] | "
        f"Position: {position}"
    )
    
    return "HOLD", False, reason


# Optional: Enhanced version with additional filters
def compute_bollinger_break_signal_enhanced(
    candles: List[Dict],
    period: int = 14,
    deviation: float = 1.0,
    min_breakout_pct: float = 0.01  # Minimum 0.01% breakout to avoid false signals
) -> Tuple[str, bool, str]:
    """
    Enhanced Bollinger Band breakout signal with additional filters
    
    Additional filters:
    - Minimum breakout percentage to filter noise
    - Candle body strength validation (avoid doji candles)
    - Volume confirmation (if available)
    
    Args:
        candles: List of OHLC candle dictionaries
        period: Bollinger Band period
        deviation: Standard deviation multiplier
        min_breakout_pct: Minimum breakout percentage (default: 0.01%)
    
    Returns:
        Tuple of (signal, should_trade, reason)
    """
    # Get basic signal
    signal, should_trade, reason = compute_bollinger_break_signal(candles, period, deviation)
    
    if not should_trade:
        return signal, False, reason
    
    # Apply additional filters
    last_candle = candles[-1]
    candle_open = float(last_candle.get('open', 0))
    candle_close = float(last_candle.get('close', 0))
    
    # Calculate candle body strength
    candle_range = abs(float(last_candle.get('max', 0)) - float(last_candle.get('min', 0)))
    candle_body = abs(candle_close - candle_open)
    
    if candle_range == 0:
        return "HOLD", False, "Invalid candle: zero range"
    
    body_ratio = (candle_body / candle_range) * 100
    
    # Reject weak candles (body < 40% of total range = likely doji/spinning top)
    if body_ratio < 40:
        return "HOLD", False, f"Weak candle body: {body_ratio:.1f}% (need >40%)"
    
    # Get BB bands
    upper_band, middle_band, lower_band = calculate_bollinger_bands(candles, period, deviation)
    bb_upper = upper_band[-1]
    bb_lower = lower_band[-1]
    
    # Validate minimum breakout strength
    if signal == "CALL":
        breakout_pct = ((candle_close - bb_upper) / bb_upper) * 100
        if breakout_pct < min_breakout_pct:
            return "HOLD", False, f"Breakout too weak: {breakout_pct:.3f}% (need >{min_breakout_pct}%)"
    
    elif signal == "PUT":
        breakout_pct = ((bb_lower - candle_close) / bb_lower) * 100
        if breakout_pct < min_breakout_pct:
            return "HOLD", False, f"Breakout too weak: {breakout_pct:.3f}% (need >{min_breakout_pct}%)"
    
    # All filters passed
    enhanced_reason = f"{reason} | Body: {body_ratio:.1f}% ✓"
    return signal, True, enhanced_reason


if __name__ == "__main__":
    """
    Test the Bollinger Break strategy with sample data
    """
    # Sample test data (simulating a breakout scenario)
    test_candles = [
        {'open': 1.1000, 'close': 1.1010, 'max': 1.1015, 'min': 1.0995},
        {'open': 1.1010, 'close': 1.1005, 'max': 1.1020, 'min': 1.1000},
        {'open': 1.1005, 'close': 1.1015, 'max': 1.1025, 'min': 1.1000},
        {'open': 1.1015, 'close': 1.1020, 'max': 1.1030, 'min': 1.1010},
        {'open': 1.1020, 'close': 1.1018, 'max': 1.1025, 'min': 1.1012},
        {'open': 1.1018, 'close': 1.1025, 'max': 1.1030, 'min': 1.1015},
        {'open': 1.1025, 'close': 1.1022, 'max': 1.1028, 'min': 1.1018},
        {'open': 1.1022, 'close': 1.1028, 'max': 1.1035, 'min': 1.1020},
        {'open': 1.1028, 'close': 1.1030, 'max': 1.1038, 'min': 1.1025},
        {'open': 1.1030, 'close': 1.1027, 'max': 1.1035, 'min': 1.1022},
        {'open': 1.1027, 'close': 1.1032, 'max': 1.1040, 'min': 1.1025},
        {'open': 1.1032, 'close': 1.1035, 'max': 1.1042, 'min': 1.1030},
        {'open': 1.1035, 'close': 1.1038, 'max': 1.1045, 'min': 1.1032},
        {'open': 1.1038, 'close': 1.1040, 'max': 1.1048, 'min': 1.1035},
        # Breakout candle: opens below BB upper, closes above
        {'open': 1.1030, 'close': 1.1055, 'max': 1.1060, 'min': 1.1028},
    ]
    
    print("=" * 80)
    print("BOLLINGER BREAK STRATEGY TEST")
    print("=" * 80)
    
    # Test basic signal
    signal, should_trade, reason = compute_bollinger_break_signal(test_candles, period=14, deviation=1.0)
    print(f"\n📊 Basic Signal:")
    print(f"   Signal: {signal}")
    print(f"   Should Trade: {should_trade}")
    print(f"   Reason: {reason}")
    
    # Test enhanced signal
    signal_enh, should_trade_enh, reason_enh = compute_bollinger_break_signal_enhanced(
        test_candles, 
        period=14, 
        deviation=1.0,
        min_breakout_pct=0.01
    )
    print(f"\n📊 Enhanced Signal (with filters):")
    print(f"   Signal: {signal_enh}")
    print(f"   Should Trade: {should_trade_enh}")
    print(f"   Reason: {reason_enh}")
    
    # Show Bollinger Band values
    upper, middle, lower = calculate_bollinger_bands(test_candles, period=14, deviation=1.0)
    if upper:
        print(f"\n📈 Bollinger Bands (last candle):")
        print(f"   Upper Band: {upper[-1]:.5f}")
        print(f"   Middle Band: {middle[-1]:.5f}")
        print(f"   Lower Band: {lower[-1]:.5f}")
        print(f"   Last Close: {test_candles[-1]['close']:.5f}")
    
    print("\n" + "=" * 80)
