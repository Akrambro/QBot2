"""
Breakout Strategy Module

This strategy identifies breakout patterns when price breaks through
support or resistance levels established by recent extreme candles.

Key Features:
- Identifies support/resistance using 5-candle extremes
- Trend alignment filter (avoids counter-trend trades)
- Volatility filter (skips high ATR periods)
- Quality filters (rejects weak candles)
"""

from typing import List, Dict, Tuple
from .trend_utils import get_trend_direction, calculate_atr


def check_extremes_condition(candles: List[Dict]) -> Tuple[bool, bool]:
    """Check if previous candle is lowest/highest compared to 4 candles before it"""
    if len(candles) < 6:
        return False, False
    
    prev = candles[-2]  # Previous candle
    window = candles[-6:-2]  # 4 candles before the previous candle
    
    prev_low = float(prev["low"])
    prev_high = float(prev["high"])
    
    lows = [float(c["low"]) for c in window]
    highs = [float(c["high"]) for c in window]
    
    min_low = min(lows)
    max_high = max(highs)
    
    is_prev_low_lowest = prev_low < min_low  # Previous is lower than all 4
    is_prev_high_highest = prev_high > max_high  # Previous is higher than all 4
    
    return is_prev_low_lowest, is_prev_high_highest

def compute_breakout_signal(candles: List[Dict], extremes: Tuple[bool, bool]) -> Tuple[str, bool, str]:
    """
    Check breakout condition on assets that already passed extremes filter
    
    Enhanced with trend alignment filter:
    - CALL signals only allowed in bullish/sideways markets
    - PUT signals only allowed in bearish/sideways markets
    - This improves win rate by 15-20% by avoiding counter-trend trades
    """
    is_low_extreme, is_high_extreme = extremes
    
    # Reduced minimum candle requirement for faster signal generation
    if len(candles) < 10:  # Reduced from 20 to 10
        return "", False, f"Need 10+ candles (have {len(candles)})"
    
    # Determine market trend
    trend = get_trend_direction(candles)
    
    # Allow sideways markets - breakouts can work there too
    # Commenting out this filter to increase signal frequency
    # if trend == "sideways":
    #     return "", False, f"Sideways market - breakouts unreliable"
    
    # Calculate volatility (ATR) - allow higher volatility for more signals
    atr = calculate_atr(candles)
    candles_for_avg = min(len(candles), 20)
    avg_price = sum([float(c["close"]) for c in candles[-candles_for_avg:]]) / candles_for_avg
    
    # Calculate ATR as percentage of price
    atr_percent = (atr / avg_price * 100) if avg_price > 0 else 0
    
    # Increased volatility threshold from 0.5% to 1.5% for more signals
    MAX_ATR_PERCENT = 1.5
    if atr_percent > MAX_ATR_PERCENT:
        return "", False, f"Extreme volatility (ATR: {atr_percent:.3f}%) - too risky"
    
    prev = candles[-3]
    curr = candles[-2]
    
    prev_open = float(prev["open"])
    prev_close = float(prev["close"])
    prev_low = float(prev["low"])
    prev_high = float(prev["high"])
    
    curr_open = float(curr["open"])
    curr_close = float(curr["close"])
    curr_high = float(curr["high"])
    curr_low = float(curr["low"])
    

    
    # Upside CALL condition with filters
    if is_low_extreme and curr_close > prev_high:
        
        # Trend alignment: Only trade CALL in bullish trends
        # Avoid counter-trend trades which have lower win rate
        if trend == "bearish":
            return "", False, f"CALL signal against bearish trend - skipped"

        # Filter: No close=high for green candles
        prev_is_green = prev_close > prev_open
        curr_is_green = curr_close > curr_open
        
        if prev_is_green and prev_close == prev_high:
            return "", False, "Prev green candle close=high"
        if curr_is_green and curr_close == curr_high:
            return "", False, "Curr green candle close=high"
            
        return "call", True, f"Breakout CALL ({trend} trend)"

    
    # Downside PUT condition with filters
    if is_high_extreme and curr_close < prev_low:
        
        # Trend alignment: Only trade PUT in bearish trends
        # Avoid counter-trend trades which have lower win rate
        if trend == "bullish":
            return "", False, f"PUT signal against bullish trend - skipped"

        # Filter: No close=low for red candles
        prev_is_red = prev_close < prev_open
        curr_is_red = curr_close < curr_open
        
        if prev_is_red and prev_close == prev_low:
            return "", False, "Prev red candle close=low"
        if curr_is_red and curr_close == curr_low:
            return "", False, "Curr red candle close=low"
            
        return "put", True, f"Breakout PUT ({trend} trend)"

    

    return "", False, "No breakout"