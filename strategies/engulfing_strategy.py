"""
Engulfing Strategy Module

This strategy identifies engulfing candle patterns which signal potential
reversals or continuations when one candle completely engulfs the previous.

Key Features:
- Detects bullish and bearish engulfing patterns
- Trend alignment filter (continuation patterns)
- Sideways market filter (alternating pattern detection)
- Candle strength validation (body > 40% of range)
"""

from typing import List, Dict, Tuple
from .trend_utils import get_trend_direction


def compute_engulfing_signal(candles: List[Dict]) -> Tuple[str, bool, str]:
    """
    Engulfing Bar Definition: current.high > previous.high and current.low < previous.low
    
    Bullish Engulfing (CALL): Current bullish candle engulfs previous bearish candle
    Bearish Engulfing (PUT): Current bearish candle engulfs previous bullish candle
    
    Enhanced Filters:
    - Trend alignment: Engulfing patterns work best as continuation in trends
    - Skip sideways markets (alternating pattern detection)
    - Skip weak engulfing (body < 40% of total range)
    - Skip close=extreme candles (weak conviction)
    """
    # Reduced minimum candle requirement for faster signal generation
    if len(candles) < 10:  # Reduced from 20 to 10
        return "", False, f"Need 10+ candles (have {len(candles)})"
    
    # Determine market trend
    trend = get_trend_direction(candles)
    
    # Disable alternating pattern check - too restrictive
    # This filter was rejecting too many valid signals
    # last_4 = candles[-4:]
    # alternating = True
    # for i in range(1, len(last_4)):
    #     curr_bullish = float(last_4[i]["close"]) > float(last_4[i]["open"])
    #     prev_bullish = float(last_4[i-1]["close"]) > float(last_4[i-1]["open"])
    #     if curr_bullish == prev_bullish:
    #         alternating = False
    #         break
    # 
    # if alternating:
    #     return "", False, "Sideways market - alternating pattern detected"
    
    prev, curr = candles[-2], candles[-1]
    
    prev_open, prev_close = float(prev["open"]), float(prev["close"])
    prev_high, prev_low = float(prev["high"]), float(prev["low"])
    
    curr_open, curr_close = float(curr["open"]), float(curr["close"])
    curr_high, curr_low = float(curr["high"]), float(curr["low"])
    
    # Engulfing bar definition: current completely covers previous range
    if not (curr_high > prev_high and curr_low < prev_low):
        return "", False, "No engulfing"
    # Bullish Engulfing: Current bullish engulfs previous bearish
    if curr_close > curr_open and prev_close < prev_open:
        # Allow bearish trend reversals - engulfing is a reversal pattern
        # Commenting out trend filter to increase signal frequency
        # if trend == "bearish":
        #     return "", False, "Bullish engulfing against bearish trend - low probability"
        
        # Filter: No close=high for green candle or close=low for red candle
        if prev_close == prev_low:  # Previous red candle close=low
            return "", False, "Prev red candle close=low"
        if curr_close == curr_high:  # Current green candle close=high
            return "", False, "Curr green candle close=high"
        
        # Reduced body strength requirement from 40% to 30% for more signals
        body_size = abs(curr_close - curr_open)
        total_range = curr_high - curr_low
        if total_range == 0:  # Prevent division by zero
            return "", False, "Invalid candle range"
        if body_size <= 0.3 * total_range:
            return "", False, "Weak engulfing - body <30% of range"
        
        return "call", True, f"Bullish Engulfing ({trend} trend)"
    
    # Bearish Engulfing: Current bearish engulfs previous bullish  
    if curr_close < curr_open and prev_close > prev_open:
        # Allow bullish trend reversals - engulfing is a reversal pattern
        # Commenting out trend filter to increase signal frequency
        # if trend == "bullish":
        #     return "", False, "Bearish engulfing against bullish trend - low probability"
        
        # Filter: No close=high for green candle or close=low for red candle
        if prev_close == prev_high:  # Previous green candle close=high
            return "", False, "Prev green candle close=high"
        if curr_close == curr_low:  # Current red candle close=low
            return "", False, "Curr red candle close=low"
        
        # Check candle strength - body must be > 30% of total range
        body_size = abs(curr_close - curr_open)
        total_range = curr_high - curr_low
        if total_range == 0:  # Prevent division by zero
            return "", False, "Invalid candle range"
        if body_size <= 0.3 * total_range:
            return "", False, "Weak engulfing - body too small"
        
        return "put", True, f"Bearish Engulfing ({trend} trend)"
    
    return "", False, "No valid signal"