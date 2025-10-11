# Engulfing Strategy Implementation
# Exact logic as specified in requirements

def compute_engulfing_signal(candles):
    """
    Engulfing Bar Definition: current.high > previous.high and current.low < previous.low
    
    Bullish Engulfing (CALL): Current bullish candle engulfs previous bearish candle
    Bearish Engulfing (PUT): Current bearish candle engulfs previous bullish candle
    
    Filters:
    - Skip if last 4 candles are alternating (sideways market)
    - Skip if engulfing candle has very long wicks (weak conviction)
    """
    if len(candles) < 6:
        return "", False, "Insufficient candles"
    
    # Check for sideways market (alternating pattern in last 4 candles)
    last_4 = candles[-4:]
    alternating = True
    for i in range(1, len(last_4)):
        curr_bullish = float(last_4[i]["close"]) > float(last_4[i]["open"])
        prev_bullish = float(last_4[i-1]["close"]) > float(last_4[i-1]["open"])
        if curr_bullish == prev_bullish:
            alternating = False
            break
    
    if alternating:
        return "", False, "Sideways market"
    
    prev, curr = candles[-2], candles[-1]
    
    prev_open, prev_close = float(prev["open"]), float(prev["close"])
    prev_high, prev_low = float(prev["high"]), float(prev["low"])
    
    curr_open, curr_close = float(curr["open"]), float(curr["close"])
    curr_high, curr_low = float(curr["high"]), float(curr["low"])
    
    # Engulfing bar definition: current completely covers previous range
    if not (curr_high > prev_high and curr_low < prev_low):
        return "", False, "No engulfing"
    
    # Check candle strength - body must be > 50% of total range
    body_size = abs(curr_close - curr_open)
    total_range = curr_high - curr_low
    if body_size <= 0.5 * total_range:
        return "", False, "Weak engulfing"
    
    # Bullish Engulfing: Current bullish engulfs previous bearish
    if curr_close > curr_open and prev_close < prev_open:
        # Filter: No close=high for green candle or close=low for red candle
        if prev_close == prev_low:  # Previous red candle close=low
            return "", False, "Prev red candle close=low"
        if curr_close == curr_high:  # Current green candle close=high
            return "", False, "Curr green candle close=high"
            
        return "call", True, "Bullish Engulfing"
    
    # Bearish Engulfing: Current bearish engulfs previous bullish  
    if curr_close < curr_open and prev_close > prev_open:
        # Filter: No close=high for green candle or close=low for red candle
        if prev_close == prev_high:  # Previous green candle close=high
            return "", False, "Prev green candle close=high"
        if curr_close == curr_low:  # Current red candle close=low
            return "", False, "Curr red candle close=low"
            
        return "put", True, "Bearish Engulfing"
    
    return "", False, "No valid signal"