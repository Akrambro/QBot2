"""
Test optimized strategy parameters

This script tests the newly optimized parameters to verify improvements.
"""

from backtest_engine import BacktestEngine
import json

def test_all_strategies():
    """Test all strategies with optimized parameters"""
    
    print("="*80)
    print("🧪 TESTING OPTIMIZED STRATEGY PARAMETERS")
    print("="*80)
    
    # Initialize engine
    engine = BacktestEngine(
        data_path="data/usdjpy_100k.csv",
        payout_rate=0.85,
        trade_amount=10.0
    )
    
    results_summary = {}
    
    # Test 1: Optimized Bollinger Band (period=20, deviation=2.0)
    print("\n" + "="*80)
    print("1️⃣ BOLLINGER BAND (Optimized: Period=20, Deviation=2.0)")
    print("="*80)
    
    bb_result = engine.backtest_bollinger(
        period=20,
        deviation=2.0,
        lookback=50,
        start_candle=100,
        end_candle=None
    )
    
    results_summary['bollinger_optimized'] = {
        'period': 20,
        'deviation': 2.0,
        'total_trades': bb_result['total_trades'],
        'win_rate': bb_result['win_rate'],
        'total_profit': bb_result['total_profit'],
        'profit_factor': bb_result['profit_factor'],
        'expected_value': bb_result['expected_value']
    }
    
    # Test 2: Baseline Bollinger Band (period=14, deviation=1.0)
    print("\n" + "="*80)
    print("2️⃣ BOLLINGER BAND (Baseline: Period=14, Deviation=1.0)")
    print("="*80)
    
    bb_baseline = engine.backtest_bollinger(
        period=14,
        deviation=1.0,
        lookback=50,
        start_candle=100,
        end_candle=None
    )
    
    results_summary['bollinger_baseline'] = {
        'period': 14,
        'deviation': 1.0,
        'total_trades': bb_baseline['total_trades'],
        'win_rate': bb_baseline['win_rate'],
        'total_profit': bb_baseline['total_profit'],
        'profit_factor': bb_baseline['profit_factor'],
        'expected_value': bb_baseline['expected_value']
    }
    
    # Test 3: Breakout Strategy
    print("\n" + "="*80)
    print("3️⃣ BREAKOUT STRATEGY (Lookback=30)")
    print("="*80)
    
    breakout_result = engine.backtest_breakout(
        lookback=30,
        start_candle=100,
        end_candle=None
    )
    
    results_summary['breakout'] = {
        'lookback': 30,
        'total_trades': breakout_result['total_trades'],
        'win_rate': breakout_result['win_rate'],
        'total_profit': breakout_result['total_profit'],
        'profit_factor': breakout_result['profit_factor'],
        'expected_value': breakout_result['expected_value']
    }
    
    # Test 4: Engulfing Strategy
    print("\n" + "="*80)
    print("4️⃣ ENGULFING STRATEGY (Lookback=30)")
    print("="*80)
    
    engulfing_result = engine.backtest_engulfing(
        lookback=30,
        start_candle=100,
        end_candle=None
    )
    
    results_summary['engulfing'] = {
        'lookback': 30,
        'total_trades': engulfing_result['total_trades'],
        'win_rate': engulfing_result['win_rate'],
        'total_profit': engulfing_result['total_profit'],
        'profit_factor': engulfing_result['profit_factor'],
        'expected_value': engulfing_result['expected_value']
    }
    
    # Comparison
    print("\n" + "="*80)
    print("📊 RESULTS COMPARISON")
    print("="*80)
    
    print(f"\n{'Strategy':<30} {'Trades':<10} {'Win Rate':<12} {'Profit':<15} {'PF':<8}")
    print("-" * 80)
    
    for name, result in results_summary.items():
        print(f"{name:<30} {result['total_trades']:<10} {result['win_rate']:<11.2f}% "
              f"${result['total_profit']:<14.2f} {result['profit_factor']:<7.2f}x")
    
    # Check improvements
    print("\n" + "="*80)
    print("💡 IMPROVEMENT ANALYSIS")
    print("="*80)
    
    opt = results_summary['bollinger_optimized']
    base = results_summary['bollinger_baseline']
    
    if opt['total_trades'] > 0 and base['total_trades'] > 0:
        wr_improvement = opt['win_rate'] - base['win_rate']
        profit_improvement = opt['total_profit'] - base['total_profit']
        trades_reduction = base['total_trades'] - opt['total_trades']
        
        print(f"\nBollinger Band Optimizations:")
        print(f"  Win Rate: {base['win_rate']:.2f}% → {opt['win_rate']:.2f}% ({wr_improvement:+.2f}%)")
        print(f"  Profit: ${base['total_profit']:.2f} → ${opt['total_profit']:.2f} (${profit_improvement:+.2f})")
        print(f"  Trades: {base['total_trades']} → {opt['total_trades']} ({-trades_reduction:+d} signals)")
        print(f"  Expected Value: ${base['expected_value']:.2f} → ${opt['expected_value']:.2f}")
        
        if wr_improvement > 0:
            print(f"\n  ✅ Win rate improved by {wr_improvement:.2f}%")
        if profit_improvement > 0:
            print(f"  ✅ Profit improved by ${profit_improvement:.2f}")
        if opt['win_rate'] > 54:
            print(f"  ✅ Win rate above profitable threshold (>54%)")
        else:
            print(f"  ⚠️  Win rate still below 54% threshold (need {54 - opt['win_rate']:.2f}% more)")
    
    # Save results
    with open('optimization_test_results.json', 'w') as f:
        json.dump(results_summary, f, indent=2)
    
    print("\n✅ Results saved to: optimization_test_results.json")
    print("="*80)


if __name__ == "__main__":
    test_all_strategies()
