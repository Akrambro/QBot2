# 📊 QBot2 Backtesting System

Comprehensive backtesting and parameter optimization framework for QBot2 trading strategies.

## 🎯 Overview

This backtesting system allows you to:
- ✅ Test strategies on historical data (100K+ candles)
- ✅ Optimize parameters with grid search
- ✅ Visualize performance with interactive charts
- ✅ Compare multiple strategies side-by-side
- ✅ Calculate risk metrics (drawdown, profit factor, Sharpe ratio)
- ✅ Export results to JSON/CSV for further analysis

## 📁 Files

### Core Components

- **`backtest_engine.py`** - Main backtesting engine
  - `BacktestEngine` class with strategy testing methods
  - Walk-forward simulation (no lookahead bias)
  - Realistic Quotex payout modeling (85% on wins, -100% on losses)
  - Comprehensive metrics calculation

- **`optimize_strategies.py`** - Parameter optimization
  - Grid search for optimal parameters
  - Bollinger Band: period (10-25) × deviation (0.5-2.5)
  - Heatmap visualizations for parameter sensitivity
  - Top performers ranking by multiple metrics

- **`run_backtest.py`** - Quick backtest runner
  - Tests all 3 strategies with default parameters
  - Side-by-side comparison
  - Generates interactive HTML charts

### Data

- **`data/usdjpy_100k.csv`** - Historical data
  - Format: Tab-separated (datetime, open, high, low, close, volume)
  - Asset: USD/JPY
  - Timeframe: 1-minute candles
  - Count: 100,000 candles (~69 days)

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Required libraries:
- `pandas` - Data manipulation
- `numpy` - Numerical computations
- `matplotlib` - Static charts
- `plotly` - Interactive visualizations
- `kaleido` - Plot export support

### 2. Run Quick Backtest (All Strategies)

```bash
python run_backtest.py
```

This will:
- Test all 3 strategies (Breakout, Engulfing, Bollinger)
- Generate `backtest_results.html` (interactive charts)
- Export `backtest_results.json` (detailed metrics)
- Print performance comparison table

**Expected Output:**
```
🚀 QBot2 Quick Backtest - All Strategies
================================================================================
📊 Initializing backtest engine...
✅ Loaded 100000 candles from 2025-07-14 03:06:00 to ...

🔬 RUNNING BACKTESTS
================================================================================

[1/3] Testing Breakout Strategy...
   Total Trades: 245
   Wins: 132 | Losses: 113
   Win Rate: 53.88%
   Total Profit: $127.50
   ...

📊 STRATEGY COMPARISON
================================================================================
Rank   Strategy        Trades     Win Rate     Profit       PF       Max DD
--------------------------------------------------------------------------------
🥇 1    Bollinger       328        58.23%       $542.30      2.14     $85.20
🥈 2    Breakout        245        53.88%       $127.50      1.48     $120.40
🥉 3    Engulfing       189        51.32%       $45.80       1.12     $95.60
```

### 3. Optimize Bollinger Band Parameters

```bash
python optimize_strategies.py
```

This will:
- Test 256 parameter combinations (16 periods × 16 deviations)
- Create heatmaps showing profit/win rate by parameters
- Export `bollinger_optimization_heatmap.html`
- Export `optimization_bollinger.csv`
- Print top 5 performers by each metric

**Sample Output:**
```
🔧 BOLLINGER BAND PARAMETER OPTIMIZATION
================================================================================
Period Range: 10 - 25 (step: 1)
Deviation Range: 0.50 - 2.50 (step: 0.25)
Total combinations to test: 256

[1/256] Testing Period=10, Deviation=0.50... ✓ Profit: $23.50
[2/256] Testing Period=10, Deviation=0.75... ✓ Profit: $87.20
...

🏆 TOP 5 PARAMETER COMBINATIONS - Bollinger Band
================================================================================

📈 By Total Profit:
   Period=14, Dev=1.25 → Profit: $642.50, Win Rate: 59.2%, Trades: 287
   Period=15, Dev=1.00 → Profit: $598.30, Win Rate: 57.8%, Trades: 312
   ...
```

## 📈 Understanding Results

### Metrics Explained

| Metric | Description | Good Value |
|--------|-------------|------------|
| **Win Rate** | % of winning trades | > 55% (for 85% payout) |
| **Total Profit** | Net P/L over all trades | Positive |
| **Profit Factor** | Gross profit ÷ Gross loss | > 1.5 |
| **Max Drawdown** | Largest equity decline | < 20% of balance |
| **Expected Value** | Average profit per trade | Positive |

### Break-Even Win Rate

With 85% payout:
- Win: +$8.50 (on $10 trade)
- Loss: -$10.00

Break-even = 100 / (100 + 85) = **54.05%**

**Any strategy with >54% win rate should be profitable!**

### Interpreting Heatmaps

In `bollinger_optimization_heatmap.html`:

1. **Total Profit** - Look for dark green zones
   - Dark green = High profit
   - Red = Losses

2. **Win Rate** - Look for dark blue zones
   - Must be > 54% to be profitable

3. **Profit Factor** - Higher is better
   - > 2.0 = Excellent
   - 1.5-2.0 = Good
   - 1.0-1.5 = Marginal

4. **Total Trades** - Ensure sufficient data
   - < 50 trades = Not statistically significant
   - 100-300 = Reasonable
   - > 300 = High confidence

## 🔬 Advanced Usage

### Custom Backtest Period

```python
from backtest_engine import BacktestEngine

engine = BacktestEngine(
    data_path="data/usdjpy_100k.csv",
    payout_rate=0.85,
    trade_amount=10.0
)

# Test only first 50,000 candles
results = engine.backtest_bollinger(
    period=14,
    deviation=1.0,
    start_candle=100,
    end_candle=50000
)
```

### Test Multiple Assets

If you have multiple CSV files:

```python
assets = ['usdjpy_100k.csv', 'eurusd_100k.csv', 'gbpusd_100k.csv']

for asset in assets:
    engine = BacktestEngine(data_path=f"data/{asset}")
    results = engine.backtest_breakout()
    print(f"{asset}: ${results['total_profit']:.2f}")
```

### Custom Optimization Ranges

```python
from optimize_strategies import StrategyOptimizer

optimizer = StrategyOptimizer("data/usdjpy_100k.csv")

# Fine-tune around best parameters
results = optimizer.optimize_bollinger(
    period_range=(12, 16),      # Narrow range
    deviation_range=(0.8, 1.4),
    period_step=1,
    deviation_step=0.1          # Finer granularity
)
```

## 📊 Output Files

### `backtest_results.html`

Interactive Plotly dashboard with 6 panels:
1. **Equity Curves** - Cumulative P/L over time
2. **Win Rate Comparison** - Bar chart
3. **Profit/Loss Distribution** - Wins vs losses by strategy
4. **Trade Distribution** - Total trades per strategy
5. **Cumulative Performance** - Time-series P/L
6. **Risk Metrics** - Max drawdown comparison

### `backtest_results.json`

Detailed metrics for each strategy:
```json
{
  "breakout": {
    "total_trades": 245,
    "win_rate": 53.88,
    "total_profit": 127.50,
    "profit_factor": 1.48,
    "max_drawdown": 120.40,
    ...
  },
  ...
}
```

### `bollinger_optimization_heatmap.html`

4-panel heatmap showing:
- Total profit by (period × deviation)
- Win rate by (period × deviation)
- Profit factor by (period × deviation)
- Trade count by (period × deviation)

### `optimization_bollinger.csv`

Exportable spreadsheet with all tested combinations:
```csv
period,deviation,total_trades,win_rate,total_profit,profit_factor,...
10,0.50,156,52.3,23.50,1.21,...
10,0.75,189,54.8,87.20,1.45,...
...
```

## 🎯 Next Steps After Backtesting

### If Strategies Are Profitable:

1. **Verify on Different Data**
   - Test on other currency pairs
   - Test different time periods
   - Confirm consistency

2. **Walk-Forward Optimization**
   - Optimize on 70% of data
   - Validate on remaining 30%
   - Check if performance holds

3. **Paper Trading**
   - Run live with practice mode
   - Monitor for 1-2 weeks
   - Compare to backtest results

4. **Live Deployment**
   - Start with minimum trade size
   - Use optimal parameters from backtesting
   - Track performance daily

### If Strategies Are NOT Profitable:

1. **Analyze Losing Trades**
   - Check `backtest_results.json` trade list
   - Identify common patterns in losses
   - Look for market conditions to avoid

2. **Adjust Strategy Logic**
   - Modify filters in `strategies/` directory
   - Add additional confirmation signals
   - Implement time-of-day filters

3. **Test Different Markets**
   - Some strategies work better on certain pairs
   - Try forex, commodities, indices

4. **Consider Market Regime**
   - Trending vs ranging markets
   - High volatility vs low volatility
   - May need regime detection

## ⚠️ Important Notes

### Backtesting Limitations

1. **Overfitting Risk**
   - More parameters = higher overfitting risk
   - Validate on out-of-sample data
   - Prefer simpler strategies

2. **No Lookahead Bias**
   - Engine only uses past candles for signals
   - Trades placed on NEXT candle (realistic)
   - Exit prices from actual future candles

3. **Execution Assumptions**
   - Assumes 100% fill rate (may not be realistic)
   - No slippage modeling (minimal for binary options)
   - Fixed 85% payout (actual may vary 80-90%)

4. **Data Quality**
   - Ensure CSV has clean OHLC data
   - Remove outliers/data errors
   - Check for gaps in timestamps

### Statistical Significance

Minimum trades for confidence:
- < 30 trades: Not reliable
- 30-100 trades: Low confidence
- 100-300 trades: Moderate confidence
- 300+ trades: High confidence

## 🛠️ Troubleshooting

### Error: "No module named 'pandas'"

```bash
pip install pandas numpy matplotlib plotly kaleido
```

### Error: "File not found: data/usdjpy_100k.csv"

- Ensure CSV file exists in `data/` directory
- Check file path in script

### Charts not displaying

- Install `kaleido` for static exports
- Open `.html` files in web browser (Chrome/Firefox)

### Memory errors with large datasets

- Reduce `end_candle` parameter
- Process data in chunks
- Increase system RAM or use smaller datasets

## 📞 Support

For issues or questions:
1. Check the code comments in `backtest_engine.py`
2. Review example usage in `run_backtest.py`
3. Examine the Plotly charts for visual debugging

---

**Happy Backtesting! 🚀📈**
