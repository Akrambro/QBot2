from typing import List, Dict, Tuple

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
    """Check breakout condition on assets that already passed extremes filter"""
    is_low_extreme, is_high_extreme = extremes
    
    if len(candles) < 6:
        return "", False, "Insufficient candles"
    
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

        # Filter: No close=high for green candles
        prev_is_green = prev_close > prev_open
        curr_is_green = curr_close > curr_open
        
        if prev_is_green and prev_close == prev_high:
            return "", False, "Prev green candle close=high"
        if curr_is_green and curr_close == curr_high:
            return "", False, "Curr green candle close=high"
            
        return "call", True, "Breakout CALL"

    
    # Downside PUT condition with filters
    if is_high_extreme and curr_close < prev_low:

        # Filter: No close=low for red candles
        prev_is_red = prev_close < prev_open
        curr_is_red = curr_close < curr_open
        
        if prev_is_red and prev_close == prev_low:
            return "", False, "Prev red candle close=low"
        if curr_is_red and curr_close == curr_low:
            return "", False, "Curr red candle close=low"
            
        return "put", True, "Breakout PUT"

    

    return "", False, "No breakout"