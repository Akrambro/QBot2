# 🚀 QBot2 Backtesting Framework - Complete Guide

## 📋 Table of Contents
1. [Quick Start](#quick-start)
2. [System Architecture](#system-architecture)
3. [Available Scripts](#available-scripts)
4. [Results Interpretation](#results-interpretation)
5. [Optimization Guide](#optimization-guide)
6. [Best Practices](#best-practices)

---

## 🎯 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Quick Backtest (5 minutes)
```bash
python run_backtest.py
```

**Generates:**
- `backtest_results.html` - Interactive charts
- `backtest_results.json` - Detailed metrics

### 3. View Results Summary
```bash
python view_results.py
```

### 4. Run Optimization (30-60 minutes)
```bash
python optimize_strategies.py
```

**Generates:**
- `bollinger_optimization_heatmap.html` - Parameter heatmaps
- `optimization_bollinger.csv` - Full results table
- `optimization_results.json` - JSON export

---

## 🏗️ System Architecture

### Core Components

```
qbot2/
├── backtest_engine.py          # Main backtesting engine
├── optimize_strategies.py      # Parameter optimization
├── run_backtest.py             # Quick test runner
├── view_results.py             # Results viewer
│
├── strategies/                 # Trading strategies
│   ├── breakout_strategy.py
│   ├── engulfing_strategy.py
│   ├── bollinger_break.py
│   └── trend_utils.py
│
├── data/                       # Historical data
│   └── usdjpy_100k.csv        # 100K candles
│
├── backtest_results.html       # Generated charts
├── backtest_results.json       # Generated metrics
└── bollinger_optimization_heatmap.html  # Optimization results
```

### Data Flow

```
CSV Data → BacktestEngine → Strategy Testing → Metrics Calculation → Visualization
                               ↓
                    Parameter Optimization → Best Settings → Re-test
```

---

## 📜 Available Scripts

### 1. `run_backtest.py` - Quick Strategy Comparison

**Purpose:** Test all strategies with default parameters

**Usage:**
```bash
python run_backtest.py
```

**What it does:**
- Tests Breakout, Engulfing, Bollinger strategies
- Simulates 85% payout (realistic Quotex settings)
- Generates comparison charts
- Saves detailed metrics

**Runtime:** ~5 minutes for 100K candles

**Output:**
```
🥇 1  Breakout    1,479 trades   47.60%   $-1,766
🥈 2  Engulfing   2,442 trades   45.62%   $-3,811
🥉 3  Bollinger  45,636 trades   46.73%  $-61,810
```

---

### 2. `view_results.py` - Terminal Results Viewer

**Purpose:** Display backtest results in terminal (no browser needed)

**Usage:**
```bash
python view_results.py
```

**What it shows:**
- Rank by profitability
- Win rate vs break-even threshold
- Profit factor, max drawdown
- File locations and sizes

**Runtime:** Instant

---

### 3. `optimize_strategies.py` - Parameter Optimization

**Purpose:** Find optimal parameters through grid search

**Usage:**
```bash
python optimize_strategies.py
```

**What it tests:**
- **Bollinger Band:**
  - Period: 10-25 (step: 1) = 16 values
  - Deviation: 0.5-2.5 (step: 0.25) = 9 values
  - Total: 16 × 9 = 144 combinations

**Runtime:** ~30-60 minutes (depends on CPU)

**Output Files:**
- `bollinger_optimization_heatmap.html` - 4 interactive heatmaps
- `optimization_bollinger.csv` - All test results
- `optimization_results.json` - JSON format

**Console Output:**
```
🏆 TOP 5 PARAMETER COMBINATIONS - Bollinger Band
================================================================================

📈 By Total Profit:
   Period=17, Dev=1.75 → Profit: $3,245.50, Win Rate: 56.8%, Trades: 1,287
   Period=18, Dev=1.50 → Profit: $2,890.30, Win Rate: 55.9%, Trades: 1,456
   ...
```

---

### 4. `backtest_engine.py` - Core Engine (Advanced)

**Purpose:** Programmatic backtesting for custom workflows

**Usage:**
```python
from backtest_engine import BacktestEngine

# Initialize
engine = BacktestEngine(
    data_path="data/usdjpy_100k.csv",
    payout_rate=0.85,
    trade_amount=10.0
)

# Test specific strategy
results = engine.backtest_bollinger(
    period=17,
    deviation=1.75,
    start_candle=1000,
    end_candle=50000
)

print(f"Profit: ${results['total_profit']:.2f}")
print(f"Win Rate: {results['win_rate']:.2f}%")

# Plot multiple strategies
engine.backtest_breakout()
engine.backtest_engulfing()
engine.plot_results()
```

**Use Cases:**
- Walk-forward optimization
- Out-of-sample testing
- Custom date ranges
- Strategy comparison with custom parameters

---

## 📊 Results Interpretation

### Key Metrics Explained

| Metric | Description | Target Value |
|--------|-------------|--------------|
| **Win Rate** | % of winning trades | > 54.05% (break-even) |
| **Total Profit** | Net P/L | Positive |
| **Profit Factor** | Gross profit ÷ Gross loss | > 1.5 |
| **Max Drawdown** | Largest equity decline | < 20% of balance |
| **Expected Value** | Avg profit per trade | Positive |
| **Total Trades** | Number of signals | 200-3,000 (ideal) |

### Break-Even Calculation

With 85% payout:
- **Win:** +$8.50 (on $10 trade)
- **Loss:** -$10.00

Break-even win rate:
```
100 / (100 + 85) = 54.05%
```

**Any strategy with >54.05% win rate should be profitable**

### Reading the Charts

#### `backtest_results.html` (6 Panels)

1. **Equity Curves**
   - Shows cumulative P/L over trades
   - Look for: Upward slope = profitable

2. **Win Rate Comparison**
   - Bar chart of win rates
   - Look for: Bars above 54% line

3. **Profit/Loss Distribution**
   - Green bars = total wins
   - Red bars = total losses
   - Look for: Green > Red

4. **Trade Distribution**
   - Total trades per strategy
   - Look for: 500-3,000 trades (good sample)

5. **Cumulative Performance**
   - P/L over time (by date)
   - Look for: Consistent gains, not volatile

6. **Risk Metrics**
   - Max drawdown comparison
   - Look for: Smallest drawdown

#### `bollinger_optimization_heatmap.html` (4 Heatmaps)

1. **Total Profit Heatmap**
   - Dark green = High profit
   - Red = Losses
   - **Action:** Identify dark green zones

2. **Win Rate Heatmap**
   - Dark blue = High win rate
   - **Action:** Find areas > 54%

3. **Profit Factor Heatmap**
   - Yellow/Green = Good PF
   - **Action:** Look for PF > 1.5

4. **Total Trades Heatmap**
   - Orange/Red = More trades
   - **Action:** Avoid extremes (too few/many)

**Best Parameters:** Intersection of:
- ✅ Dark green profit
- ✅ Win rate > 54%
- ✅ Profit factor > 1.5
- ✅ Trade count 500-3,000

---

## 🔧 Optimization Guide

### Step-by-Step Optimization Workflow

#### 1. Run Initial Backtest
```bash
python run_backtest.py
```

**Goal:** Establish baseline performance

#### 2. Analyze Initial Results
```bash
python view_results.py
```

**Questions to ask:**
- Which strategy is closest to break-even?
- Is win rate or trade frequency the issue?
- Are there too many/too few trades?

#### 3. Run Optimization
```bash
python optimize_strategies.py
```

**What to monitor:**
- Progress: `[45/144] Testing Period=15, Deviation=1.25...`
- Early results: Look for profitable combinations

#### 4. Analyze Heatmaps

Open `bollinger_optimization_heatmap.html`:

**Look for:**
- **Dark green profit zones** (top-left heatmap)
- **Win rates > 54%** (top-right heatmap)
- **Reasonable trade count** (bottom-right heatmap)

**Example findings:**
```
Best Zone: Period 16-19, Deviation 1.5-2.0
- Profit: $2,000-$4,000
- Win Rate: 55-58%
- Trades: 800-1,500
```

#### 5. Test Best Parameters

```python
from backtest_engine import BacktestEngine

engine = BacktestEngine("data/usdjpy_100k.csv")

# Test top 3 parameter sets
results1 = engine.backtest_bollinger(period=17, deviation=1.75)
results2 = engine.backtest_bollinger(period=18, deviation=1.50)
results3 = engine.backtest_bollinger(period=16, deviation=2.00)

# Compare
print(f"Set 1: ${results1['total_profit']:.2f}")
print(f"Set 2: ${results2['total_profit']:.2f}")
print(f"Set 3: ${results3['total_profit']:.2f}")
```

#### 6. Walk-Forward Validation

**Test on unseen data to prevent overfitting:**

```python
# Train on first 70% of data
train_results = engine.backtest_bollinger(
    period=17,
    deviation=1.75,
    start_candle=100,
    end_candle=70000  # First 70K candles
)

# Test on last 30% of data
test_results = engine.backtest_bollinger(
    period=17,
    deviation=1.75,
    start_candle=70000,
    end_candle=99900  # Last 30K candles
)

print("Train Profit:", train_results['total_profit'])
print("Test Profit:", test_results['total_profit'])

# If test profit is positive, parameters are robust!
```

#### 7. Paper Trade (If Profitable)

- Update `trading_loop.py` with optimized parameters
- Run in practice mode for 1 week
- Compare live results to backtest

#### 8. Go Live (If Validated)

- Start with minimum trade size ($1)
- Scale up gradually after 100+ trades
- Monitor daily performance vs backtest

---

## ✅ Best Practices

### Do's ✅

1. **Always optimize on historical data first**
   - Never trade with default parameters
   - Test before risking money

2. **Use walk-forward validation**
   - Train/test split prevents overfitting
   - Out-of-sample testing is critical

3. **Look for consistency across time periods**
   - Strategy should work on different date ranges
   - Avoid parameter sets that only work once

4. **Consider multiple metrics**
   - Don't just maximize profit
   - Check win rate, drawdown, trade frequency

5. **Start small in live trading**
   - Paper trade first
   - Use micro-stakes initially
   - Scale up gradually

### Don'ts ❌

1. **Don't overfit parameters**
   - Using too many decimals (e.g., 1.73582)
   - Testing thousands of combinations
   - Parameters that work on 1 specific period only

2. **Don't ignore trade count**
   - < 100 trades = Not statistically significant
   - > 10,000 trades = Likely over-trading

3. **Don't cherry-pick results**
   - Test full date range, not just profitable periods
   - Include losing trades in analysis

4. **Don't skip validation**
   - Always test on out-of-sample data
   - Walk-forward is mandatory

5. **Don't expect perfection**
   - 55-60% win rate is excellent
   - Drawdowns are normal
   - No strategy wins 100%

---

## 🎓 Advanced Tips

### Optimizing Other Strategies

#### Breakout Strategy

Modify `optimize_strategies.py`:

```python
def optimize_breakout(self):
    """Optimize breakout ATR threshold"""
    results = []
    
    for atr_threshold in np.arange(0.5, 3.0, 0.25):
        # Modify breakout_strategy.py to accept atr_threshold parameter
        # Then test each value
        result = self.engine.backtest_breakout(atr_threshold=atr_threshold)
        results.append(result)
    
    return pd.DataFrame(results)
```

#### Engulfing Strategy

```python
def optimize_engulfing(self):
    """Optimize engulfing body percentage"""
    results = []
    
    for body_pct in range(20, 60, 5):
        # Modify engulfing_strategy.py to accept body_pct parameter
        result = self.engine.backtest_engulfing(body_pct=body_pct)
        results.append(result)
    
    return pd.DataFrame(results)
```

### Multi-Asset Testing

```python
assets = {
    'usdjpy': 'data/usdjpy_100k.csv',
    'eurusd': 'data/eurusd_100k.csv',
    'gbpusd': 'data/gbpusd_100k.csv'
}

for name, path in assets.items():
    engine = BacktestEngine(path)
    results = engine.backtest_bollinger(period=17, deviation=1.75)
    
    print(f"{name.upper()}: ${results['total_profit']:.2f}")
```

### Time-of-Day Analysis

```python
import pandas as pd

# Group trades by hour
trades_df = pd.DataFrame(results['trades'])
trades_df['hour'] = pd.to_datetime(trades_df['entry_time']).dt.hour

hourly_performance = trades_df.groupby('hour').agg({
    'pnl': 'sum',
    'won': lambda x: x.sum() / len(x) * 100
})

print("Best hours to trade:")
print(hourly_performance.sort_values('pnl', ascending=False).head())
```

---

## 🆘 Troubleshooting

### "No module named 'pandas'"
```bash
pip install pandas numpy matplotlib plotly kaleido
```

### "File not found: data/usdjpy_100k.csv"
- Ensure CSV file exists
- Check file path in scripts

### Charts not displaying
- Install `kaleido`: `pip install kaleido`
- Open `.html` files in browser manually

### Optimization taking too long
- Reduce parameter ranges
- Use larger step sizes
- Test on subset of data first

### All strategies unprofitable
- **This is normal!** Default parameters rarely work
- Run optimization to find profitable settings
- Consider different assets or timeframes

---

## 📚 Additional Resources

### Files Generated

| File | Size | Description |
|------|------|-------------|
| `backtest_results.html` | ~500 KB | Interactive 6-panel dashboard |
| `backtest_results.json` | ~50 KB | Detailed metrics + trade list |
| `bollinger_optimization_heatmap.html` | ~800 KB | Parameter heatmaps |
| `optimization_bollinger.csv` | ~100 KB | All tested combinations |

### Reading List

- **BACKTESTING_README.md** - Framework documentation
- **BACKTEST_ANALYSIS.md** - Current results analysis
- **strategy_analysis.md** - Strategy logic documentation

---

## 🎯 Success Checklist

Before going live:

- [ ] Backtest completed on full historical data
- [ ] Optimization run for all strategies
- [ ] Best parameters identified (win rate > 54%)
- [ ] Walk-forward validation passed
- [ ] Out-of-sample testing positive
- [ ] Paper trading for 1+ week successful
- [ ] Drawdown limits defined
- [ ] Daily stop-loss in place
- [ ] Position sizing calculated
- [ ] Risk management rules documented

---

## 📞 Next Steps

1. ✅ **Review current results** → `python view_results.py`
2. 🔧 **Run optimization** → `python optimize_strategies.py`
3. 📊 **Analyze heatmaps** → Open `.html` files
4. 🧪 **Test best parameters** → Custom backtest
5. ✅ **Validate** → Walk-forward test
6. 📝 **Paper trade** → Practice mode
7. 💰 **Go live** → Minimum stakes

---

**🚀 Ready to find profitable parameters! Good luck!**
