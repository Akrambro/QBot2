from typing import List, Dict, Tuple

def check_engulfing_signal(candles: List[Dict]) -> Tuple[str, bool]:
    """
    Detects if the current candle engulfs the previous one and predicts the next candle's direction.

    Args:
        candles: A list of dictionaries, where each dictionary represents a candle.

    Returns:
        A tuple containing the signal ('call', 'put', or '') and a boolean indicating validity.
    """
    if len(candles) < 5:  # Need at least 5 candles for the sideways check and engulfing pattern
        return "", False

    current = candles[-1]
    previous = candles[-2]

    # Engulfing Bar Definition
    is_engulfing = float(current['high']) > float(previous['high']) and float(current['low']) < float(previous['low'])

    if not is_engulfing:
        return "", False

    # Trade Signal Direction
    is_bullish_engulfing = float(current['close']) > float(current['open']) and float(previous['close']) < float(previous['open'])
    is_bearish_engulfing = float(current['close']) < float(current['open']) and float(previous['close']) > float(previous['open'])

    # No Trade Filters
    # Skip if last 4 candles are alternating (sideways market)
    last_four = candles[-5:-1]
    directions = [(float(c['close']) > float(c['open'])) for c in last_four]
    if directions == [True, False, True, False] or directions == [False, True, False, True]:
        return "", False

    # Skip if the engulfing candle has very long wicks
    candle_body = abs(float(current['close']) - float(current['open']))
    candle_range = float(current['high']) - float(current['low'])
    if candle_body <= 0.5 * candle_range:
        return "", False

    if is_bullish_engulfing:
        return "call", True

    if is_bearish_engulfing:
        return "put", True

    return "", False
