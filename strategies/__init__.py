"""
Trading Strategies Package

This package contains all trading strategy implementations for the QBot2 system.

Available Strategies:
- Breakout Strategy: Trades breakouts from support/resistance levels
- Engulfing Strategy: Trades engulfing candle patterns
- Bollinger Break: Trades Bollinger Band breakouts (period=14, deviation=1)

Shared Utilities:
- trend_utils: Common functions for trend detection and volatility measurement
"""

from .breakout_strategy import check_extremes_condition, compute_breakout_signal
from .engulfing_strategy import compute_engulfing_signal
from .bollinger_break import (
    compute_bollinger_break_signal,
    compute_bollinger_break_signal_enhanced,
    calculate_bollinger_bands
)
from .trend_utils import get_trend_direction, calculate_atr

__all__ = [
    'check_extremes_condition',
    'compute_breakout_signal',
    'compute_engulfing_signal',
    'compute_bollinger_break_signal',
    'compute_bollinger_break_signal_enhanced',
    'calculate_bollinger_bands',
    'get_trend_direction',
    'calculate_atr',
]

__version__ = '2.1.0'
