"""
Supertrend Strategy Module

This strategy identifies trend changes using the Supertrend indicator.
Signals are generated ONLY when the Supertrend line changes color
and the current candle closes completely.

Key Features:
- Supertrend calculation with configurable period and multiplier
- Signal on color change (green to red = PUT, red to green = CALL)
- Requires candle close confirmation before signaling
- Default parameters: period=8, multiplier=1

Author: QBot2 Trading System
Version: 1.0.0
"""

from typing import List, Dict, Tuple
from config import MIN_CANDLES


def calculate_atr(candles: List[Dict], period: int = 8) -> List[float]:
    """
    Calculate Average True Range (ATR)
    
    Args:
        candles: List of OHLC candle dictionaries
        period: ATR period (default: 8)
    
    Returns:
        List of ATR values
    """
    atr_values = []
    
    for i in range(len(candles)):
        if i == 0:
            # First candle: TR = high - low
            high = float(candles[i].get('high') or candles[i].get('max', 0))
            low = float(candles[i].get('low') or candles[i].get('min', 0))
            tr = high - low
            atr_values.append(tr)
        else:
            # TR = max(high - low, abs(high - prev_close), abs(low - prev_close))
            high = float(candles[i].get('high') or candles[i].get('max', 0))
            low = float(candles[i].get('low') or candles[i].get('min', 0))
            prev_close = float(candles[i-1].get('close', 0))
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            
            # Calculate ATR using smoothed moving average
            if i < period:
                # Simple average for initial period
                atr = sum([atr_values[j] if j < len(atr_values) else tr 
                          for j in range(i + 1)]) / (i + 1)
            else:
                # Smoothed ATR: (prev_atr * (period - 1) + tr) / period
                prev_atr = atr_values[i - 1]
                atr = (prev_atr * (period - 1) + tr) / period
            
            atr_values.append(atr)
    
    return atr_values


def calculate_supertrend(
    candles: List[Dict],
    period: int = 8,
    multiplier: float = 1.0
) -> Tuple[List[float], List[str]]:
    """
    Calculate Supertrend indicator
    
    Args:
        candles: List of OHLC candle dictionaries
        period: ATR period (default: 8)
        multiplier: ATR multiplier (default: 1.0)
    
    Returns:
        Tuple of (supertrend_values, trend_direction)
        - supertrend_values: List of Supertrend line values
        - trend_direction: List of 'up' or 'down' for each candle
    """
    if len(candles) < period:
        return [], []
    
    # Calculate ATR
    atr_values = calculate_atr(candles, period)
    
    supertrend = []
    trend = []
    
    for i in range(len(candles)):
        high = float(candles[i].get('high') or candles[i].get('max', 0))
        low = float(candles[i].get('low') or candles[i].get('min', 0))
        close = float(candles[i].get('close', 0))
        
        # Calculate basic bands
        hl_avg = (high + low) / 2
        atr = atr_values[i]
        
        upper_band = hl_avg + (multiplier * atr)
        lower_band = hl_avg - (multiplier * atr)
        
        if i == 0:
            # First candle: initialize
            if close > upper_band:
                supertrend.append(lower_band)
                trend.append('up')
            else:
                supertrend.append(upper_band)
                trend.append('down')
        else:
            prev_supertrend = supertrend[i - 1]
            prev_trend = trend[i - 1]
            
            # Adjust bands based on previous values
            if lower_band > prev_supertrend or candles[i - 1].get('close', 0) < prev_supertrend:
                final_lower_band = lower_band
            else:
                final_lower_band = prev_supertrend
            
            if upper_band < prev_supertrend or candles[i - 1].get('close', 0) > prev_supertrend:
                final_upper_band = upper_band
            else:
                final_upper_band = prev_supertrend
            
            # Determine trend
            if close > final_upper_band:
                current_trend = 'up'
                current_supertrend = final_lower_band
            elif close < final_lower_band:
                current_trend = 'down'
                current_supertrend = final_upper_band
            else:
                # Continue previous trend
                current_trend = prev_trend
                if current_trend == 'up':
                    current_supertrend = final_lower_band
                else:
                    current_supertrend = final_upper_band
            
            supertrend.append(current_supertrend)
            trend.append(current_trend)
    
    return supertrend, trend


def compute_supertrend_signal(
    candles: List[Dict],
    period: int = 8,
    multiplier: float = 1.0
) -> Tuple[str, bool, str]:
    """
    Generate trading signal based on Supertrend color change
    
    Signal Logic:
    - CALL: Supertrend changes from 'down' (red) to 'up' (green)
    - PUT: Supertrend changes from 'up' (green) to 'down' (red)
    - Signal ONLY generated when current candle is CLOSED and confirms the change
    
    Args:
        candles: List of OHLC candle dictionaries (most recent last)
        period: Supertrend period (default: 8)
        multiplier: Supertrend multiplier (default: 1.0)
    
    Returns:
        Tuple of (signal, should_trade, reason)
        - signal: "call", "put", or ""
        - should_trade: Boolean indicating if trade should be placed
        - reason: Explanation of the decision
    """
    # Need minimum candles for calculation
    min_required = max(period + 2, MIN_CANDLES)
    if len(candles) < min_required:
        return "", False, f"Need {min_required}+ candles (have {len(candles)})"
    
    # Calculate Supertrend
    supertrend_values, trend_direction = calculate_supertrend(candles, period, multiplier)
    
    if len(trend_direction) < 2:
        return "", False, "Insufficient Supertrend data"
    
    # Get current and previous trend
    current_trend = trend_direction[-1]
    prev_trend = trend_direction[-2]
    
    # Get current candle close
    current_close = float(candles[-1].get('close', 0))
    current_supertrend = supertrend_values[-1]
    
    # Check for trend change (color change)
    trend_changed = current_trend != prev_trend
    
    if not trend_changed:
        return "", False, f"No trend change (trend={current_trend})"
    
    # CALL signal: Trend changed from down to up (red to green)
    if prev_trend == 'down' and current_trend == 'up':
        # Verify candle closed above Supertrend
        if current_close > current_supertrend:
            reason = (
                f"CALL: Supertrend color change (down→up) | "
                f"Close={current_close:.5f} > ST={current_supertrend:.5f} | "
                f"Period={period}, Mult={multiplier}"
            )
            return "call", True, reason
        else:
            return "", False, f"Trend changed to up but close not above ST ({current_close:.5f} <= {current_supertrend:.5f})"
    
    # PUT signal: Trend changed from up to down (green to red)
    if prev_trend == 'up' and current_trend == 'down':
        # Verify candle closed below Supertrend
        if current_close < current_supertrend:
            reason = (
                f"PUT: Supertrend color change (up→down) | "
                f"Close={current_close:.5f} < ST={current_supertrend:.5f} | "
                f"Period={period}, Mult={multiplier}"
            )
            return "put", True, reason
        else:
            return "", False, f"Trend changed to down but close not below ST ({current_close:.5f} >= {current_supertrend:.5f})"
    
    return "", False, "No valid signal"


if __name__ == "__main__":
    """
    Test the Supertrend strategy with sample data
    """
    # Sample test data simulating a trend reversal
    test_candles = [
        {'open': 1.1000, 'close': 1.0995, 'high': 1.1005, 'low': 1.0990, 'max': 1.1005, 'min': 1.0990},
        {'open': 1.0995, 'close': 1.0990, 'high': 1.1000, 'low': 1.0985, 'max': 1.1000, 'min': 1.0985},
        {'open': 1.0990, 'close': 1.0988, 'high': 1.0995, 'low': 1.0980, 'max': 1.0995, 'min': 1.0980},
        {'open': 1.0988, 'close': 1.0985, 'high': 1.0992, 'low': 1.0978, 'max': 1.0992, 'min': 1.0978},
        {'open': 1.0985, 'close': 1.0980, 'high': 1.0990, 'low': 1.0975, 'max': 1.0990, 'min': 1.0975},
        {'open': 1.0980, 'close': 1.0978, 'high': 1.0985, 'low': 1.0970, 'max': 1.0985, 'min': 1.0970},
        {'open': 1.0978, 'close': 1.0975, 'high': 1.0982, 'low': 1.0968, 'max': 1.0982, 'min': 1.0968},
        {'open': 1.0975, 'close': 1.0972, 'high': 1.0980, 'low': 1.0965, 'max': 1.0980, 'min': 1.0965},
        {'open': 1.0972, 'close': 1.0970, 'high': 1.0978, 'low': 1.0963, 'max': 1.0978, 'min': 1.0963},
        # Reversal starts here
        {'open': 1.0970, 'close': 1.0985, 'high': 1.0990, 'low': 1.0968, 'max': 1.0990, 'min': 1.0968},
        {'open': 1.0985, 'close': 1.0995, 'high': 1.1000, 'low': 1.0980, 'max': 1.1000, 'min': 1.0980},
        {'open': 1.0995, 'close': 1.1005, 'high': 1.1010, 'low': 1.0990, 'max': 1.1010, 'min': 1.0990},
    ]
    
    print("=" * 80)
    print("SUPERTREND STRATEGY TEST (Period=8, Multiplier=1)")
    print("=" * 80)
    
    # Calculate Supertrend
    supertrend, trends = calculate_supertrend(test_candles, period=8, multiplier=1.0)
    
    print(f"\n📊 Supertrend Values (last 5):")
    for i in range(max(0, len(test_candles) - 5), len(test_candles)):
        candle = test_candles[i]
        st_val = supertrend[i] if i < len(supertrend) else 0
        trend_dir = trends[i] if i < len(trends) else 'N/A'
        color = '🟢' if trend_dir == 'up' else '🔴'
        print(f"   Candle {i+1}: Close={candle['close']:.4f} | ST={st_val:.4f} | {color} {trend_dir}")
    
    # Test signal
    signal, should_trade, reason = compute_supertrend_signal(test_candles, period=8, multiplier=1.0)
    
    print(f"\n📊 Signal Result:")
    print(f"   Signal: {signal.upper() if signal else 'NONE'}")
    print(f"   Should Trade: {should_trade}")
    print(f"   Reason: {reason}")
    
    print("\n" + "=" * 80)
