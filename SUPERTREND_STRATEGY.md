# Supertrend Strategy Documentation

## Overview
The Supertrend strategy generates trading signals based on trend direction changes detected by the Supertrend indicator. Signals are only generated when the Supertrend line **changes color** (trend reversal) and the current candle **closes completely**, confirming the new direction.

## Parameters
- **Period**: 8 (ATR calculation period)
- **Multiplier**: 1.0 (ATR multiplier for band calculation)

## Signal Logic

### CALL Signal (Buy)
Generated when:
1. Supertrend changes from **DOWN** (red) to **UP** (green)
2. Current candle closes **ABOVE** the Supertrend line
3. Confirms bullish trend reversal

### PUT Signal (Sell)
Generated when:
1. Supertrend changes from **UP** (green) to **DOWN** (red)
2. Current candle closes **BELOW** the Supertrend line
3. Confirms bearish trend reversal

## How Supertrend Works

### Calculation Steps
1. **Calculate ATR** (Average True Range) for the specified period
2. **Compute Basic Bands**:
   - Upper Band = (High + Low) / 2 + (Multiplier × ATR)
   - Lower Band = (High + Low) / 2 - (Multiplier × ATR)
3. **Determine Trend**:
   - **Uptrend** (green): Price closes above upper band → Supertrend = Lower Band
   - **Downtrend** (red): Price closes below lower band → Supertrend = Upper Band
4. **Detect Color Change**: Compare current trend with previous trend

## Configuration

### Environment Variables
Add to your `.env` file:

```bash
# Enable Supertrend strategy (default: enabled)
QX_SUPERTREND_ENABLED=1

# Supertrend parameters
QX_SUPERTREND_PERIOD=8
QX_SUPERTREND_MULTIPLIER=1.0
```

### Disable Other Strategies (Optional)
If you want to use **only** Supertrend:

```bash
QX_BREAKOUT_ENABLED=0
QX_ENGULFING_ENABLED=0
QX_BOLLINGER_ENABLED=0
QX_SUPERTREND_ENABLED=1
```

## Minimum Candle Requirements
- **Minimum candles**: `max(SUPERTREND_PERIOD + 2, MIN_CANDLES)`
- With default settings: **10 candles** (8 + 2)
- The strategy needs at least 2 extra candles beyond the period to detect trend changes

## Usage Examples

### In Live Trading
The bot automatically checks Supertrend when enabled:
```python
# Supertrend is checked in analyze_asset() function
if SUPERTREND_ENABLED and len(candles) >= SUPERTREND_PERIOD + 2:
    signal, valid, msg = compute_supertrend_signal(
        candles,
        period=SUPERTREND_PERIOD,
        multiplier=SUPERTREND_MULTIPLIER
    )
```

### In Backtesting
Run backtest for Supertrend:
```python
from backtest_engine import BacktestEngine

engine = BacktestEngine(
    data_path="data/usdjpy_100k.csv",
    payout_rate=0.85,
    trade_amount=10.0
)

# Backtest Supertrend with default params (8, 1.0)
results = engine.backtest_supertrend(period=8, multiplier=1.0)

# Try different parameters
results = engine.backtest_supertrend(period=10, multiplier=1.5)
```

## Trade Placement Flow
1. **Candle Close**: Wait for current candle to close completely
2. **Check Trend Change**: Compare current vs previous Supertrend trend
3. **Validate Close**: Ensure close confirms the new trend direction
4. **Generate Signal**: If conditions met, generate CALL or PUT
5. **Place Trade**: Execute trade on the **next opening candle**

## Example Output
When a Supertrend signal is detected:
```
✅ EUR/USD (OTC) SUPERTREND SIGNAL: CALL - CALL: Supertrend color change (down→up) | Close=1.09950 > ST=1.09669 | Period=8, Mult=1.0

🎯 SUPERTREND TRADE PLACED!
   Asset: EUR/USD (OTC)
   Direction: CALL
   Amount: $10.50
   Trade ID: 12345678
   ST Period: 8 | Multiplier: 1.0
```

## Advantages
- **Clear trend detection**: Supertrend clearly identifies trend direction
- **Color change confirmation**: Only trades on definitive reversals
- **Low lag**: Period=8 with Multiplier=1 is responsive to price changes
- **Works with 8+ candles**: Minimal data requirement

## Optimization Tips
- **Period**: Lower values (5-8) = more responsive, more signals
- **Multiplier**: Lower values (0.5-1.5) = tighter bands, more signals
- Test different combinations in backtesting before live use

## Risk Considerations
- Works best in **trending markets**
- May generate false signals in **choppy/sideways markets**
- Color changes can occur frequently in high volatility
- Always use proper risk management (position sizing, stop-loss limits)

## Code Location
- **Strategy Implementation**: `/workspaces/QBot2/strategies/supertrend_strategy.py`
- **Trading Integration**: `/workspaces/QBot2/trading_loop.py`
- **Backtesting**: `/workspaces/QBot2/backtest_engine.py`

## Testing
Run the standalone test:
```bash
cd /workspaces/QBot2
PYTHONPATH=/workspaces/QBot2:$PYTHONPATH python strategies/supertrend_strategy.py
```

## Related Strategies
- **Breakout**: Trades range breakouts with extreme candles
- **Engulfing**: Trades candlestick reversal patterns
- **Bollinger Break**: Trades Bollinger Band breakouts

You can enable multiple strategies simultaneously - the bot will check each in sequence and take the first valid signal found.
