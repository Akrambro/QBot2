"""
Global configuration constants for QBot2

Place common thresholds and small configuration values here so they
stay consistent across modules.
"""

# Minimum number of candles required for strategy analysis (user-adjustable)
MIN_CANDLES = 8

# Minimum number of validated normalized candles after cleaning (fetch_candles)
# Keep lower than MIN_CANDLES to allow normalization to filter bad candles
# without immediately failing. Change with care.
MIN_VALID_CANDLES = 6

# Default Bollinger minimum enforcement -- use (period + 1) but never less than MIN_CANDLES
# This isn't used directly here but documented for clarity.
DEFAULTS = {
    'MIN_CANDLES': MIN_CANDLES,
    'MIN_VALID_CANDLES': MIN_VALID_CANDLES,
}
