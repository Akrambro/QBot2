from typing import List, Dict, Tuple


def check_breakout_signal(candles: List[Dict]) -> Tuple[str, bool]:
    """Return (signal, valid) where signal is 'call'|'put'|''.

    Rules use the last 6 candles to evaluate:
    - previous = candles[-2]
    - current = candles[-1]
    - window for extremes: last 5 candles excluding current (candles[-6:-1])
    """
    if len(candles) < 6:
        return "", False

    prev = candles[-2]
    curr = candles[-1]
    window = candles[-6:-1]  # 5 candles ending at prev

    prev_low = float(prev["low"])
    prev_high = float(prev["high"])
    curr_close = float(curr["close"])

    lows = [float(c["low"]) for c in window]
    highs = [float(c["high"]) for c in window]

    is_prev_low_lowest5 = prev_low == min(lows)
    is_prev_high_highest5 = prev_high == max(highs)

    # Upside condition
    if is_prev_low_lowest5 and curr_close > float(prev["high"]):
        return "call", True

    # Downside condition
    if is_prev_high_highest5 and curr_close < float(prev["low"]):
        return "put", True

    return "", False
