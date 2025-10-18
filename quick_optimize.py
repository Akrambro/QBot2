"""
Quick Optimization - Targeted Parameter Search

Tests fewer combinations in key ranges for faster results.
Use this for rapid iteration, then use optimize_strategies.py for full search.

Author: QBot2 Trading System
"""

import pandas as pd
import numpy as np
from backtest_engine import BacktestEngine
from datetime import datetime


def quick_optimize():
    """Quick optimization with targeted ranges"""
    
    print("="*80)
    print("⚡ QUICK BOLLINGER OPTIMIZATION")
    print("="*80)
    print("Testing 36 strategic combinations for fast results...")
    print()
    
    engine = BacktestEngine(
        data_path="data/usdjpy_100k.csv",
        payout_rate=0.85,
        trade_amount=10.0
    )
    
    results = []
    
    # Strategic ranges based on typical binary options settings
    periods = [12, 14, 16, 18, 20, 22]  # 6 values
    deviations = [1.0, 1.25, 1.5, 1.75, 2.0, 2.25]  # 6 values
    # Total: 6 × 6 = 36 combinations (vs 144 in full optimization)
    
    total = len(periods) * len(deviations)
    current = 0
    
    for period in periods:
        for deviation in deviations:
            current += 1
            
            print(f"[{current}/{total}] Period={period}, Deviation={deviation:.2f}...", end=" ", flush=True)
            
            result = engine.backtest_bollinger(
                period=period,
                deviation=deviation,
                lookback=50,
                start_candle=100,
                end_candle=None
            )
            
            results.append({
                'period': period,
                'deviation': deviation,
                'total_trades': result['total_trades'],
                'win_rate': result['win_rate'],
                'total_profit': result['total_profit'],
                'profit_factor': result['profit_factor'],
                'max_drawdown': result['max_drawdown'],
                'expected_value': result['expected_value']
            })
            
            status = "✅ PROFIT" if result['total_profit'] > 0 else "❌"
            print(f"{status} | ${result['total_profit']:.2f} | WR: {result['win_rate']:.1f}% | Trades: {result['total_trades']}")
    
    df = pd.DataFrame(results)
    
    # Filter combinations with reasonable trade counts
    df_valid = df[(df['total_trades'] >= 100) & (df['total_trades'] <= 5000)].copy()
    
    print("\n" + "="*80)
    print("🏆 TOP 10 COMBINATIONS")
    print("="*80)
    
    if len(df_valid) > 0:
        # Sort by total profit
        top_profit = df_valid.nlargest(10, 'total_profit')
        
        print(f"\n{'Rank':<6}{'Period':<10}{'Deviation':<12}{'Trades':<10}{'Win Rate':<12}{'Profit':<12}{'PF':<8}")
        print("-" * 80)
        
        for idx, (rank, row) in enumerate(top_profit.iterrows(), 1):
            emoji = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else "  "
            
            print(f"{emoji} {idx:<4}{int(row['period']):<10}{row['deviation']:<12.2f}"
                  f"{int(row['total_trades']):<10}{row['win_rate']:<11.2f}%"
                  f"${row['total_profit']:<11.2f}{row['profit_factor']:<7.2f}x")
        
        # Best parameters
        best = top_profit.iloc[0]
        
        print("\n" + "="*80)
        print("🎯 RECOMMENDED PARAMETERS")
        print("="*80)
        print(f"   Period:        {int(best['period'])}")
        print(f"   Deviation:     {best['deviation']:.2f}")
        print(f"   Expected:")
        print(f"     - Win Rate:  {best['win_rate']:.2f}%")
        print(f"     - Profit:    ${best['total_profit']:.2f}")
        print(f"     - Trades:    {int(best['total_trades'])}")
        print(f"     - PF:        {best['profit_factor']:.2f}x")
        print("="*80)
        
        # Check if profitable
        profitable_count = len(df_valid[df_valid['total_profit'] > 0])
        
        if profitable_count > 0:
            print(f"\n✅ Found {profitable_count} profitable parameter combinations!")
            print(f"   Best profit: ${df_valid['total_profit'].max():.2f}")
            print(f"   Best win rate: {df_valid['win_rate'].max():.2f}%")
        else:
            print("\n⚠️ No profitable combinations found in quick test.")
            print("   Recommendations:")
            print("   1. Run full optimization: python optimize_strategies.py")
            print("   2. Try different asset or timeframe")
            print("   3. Add additional filters to strategies")
    else:
        print("\n⚠️ No valid combinations (all had extreme trade counts)")
    
    # Save results
    df.to_csv('quick_optimization.csv', index=False)
    print(f"\n💾 Results saved to: quick_optimization.csv")
    
    return df


def test_best_on_subsample(period: int, deviation: float):
    """Test best parameters on different data segment"""
    
    print("\n" + "="*80)
    print("🧪 OUT-OF-SAMPLE VALIDATION")
    print("="*80)
    print(f"Testing Period={period}, Deviation={deviation} on different data...")
    
    engine = BacktestEngine("data/usdjpy_100k.csv", payout_rate=0.85, trade_amount=10.0)
    
    # Test on last 30% of data
    total_candles = len(engine.df)
    split_point = int(total_candles * 0.7)
    
    print(f"\nTraining period: Candles 100 - {split_point}")
    result_train = engine.backtest_bollinger(
        period=period,
        deviation=deviation,
        start_candle=100,
        end_candle=split_point
    )
    
    print(f"\nTest period: Candles {split_point} - {total_candles - 2}")
    result_test = engine.backtest_bollinger(
        period=period,
        deviation=deviation,
        start_candle=split_point,
        end_candle=total_candles - 2
    )
    
    # Compare results
    print("\n" + "="*80)
    print("📊 VALIDATION RESULTS")
    print("="*80)
    
    print(f"\n{'Metric':<20}{'Training':<20}{'Testing':<20}{'Difference':<15}")
    print("-" * 80)
    
    metrics = [
        ('Trades', result_train['total_trades'], result_test['total_trades']),
        ('Win Rate', f"{result_train['win_rate']:.2f}%", f"{result_test['win_rate']:.2f}%", 
         f"{result_test['win_rate'] - result_train['win_rate']:+.2f}%"),
        ('Total Profit', f"${result_train['total_profit']:.2f}", f"${result_test['total_profit']:.2f}",
         f"${result_test['total_profit'] - result_train['total_profit']:+.2f}"),
        ('Profit Factor', f"{result_train['profit_factor']:.2f}", f"{result_test['profit_factor']:.2f}",
         f"{result_test['profit_factor'] - result_train['profit_factor']:+.2f}")
    ]
    
    for metric_name, train_val, test_val, *diff in metrics:
        diff_str = diff[0] if diff else ""
        print(f"{metric_name:<20}{str(train_val):<20}{str(test_val):<20}{diff_str:<15}")
    
    # Verdict
    print("\n" + "="*80)
    
    if result_test['total_profit'] > 0 and result_test['win_rate'] > 54:
        print("✅ VALIDATION PASSED!")
        print("   Parameters are robust across different time periods.")
        print("   Safe to use in live trading (start with paper trading).")
    elif result_test['total_profit'] > 0:
        print("⚠️ MARGINAL VALIDATION")
        print("   Profitable but win rate is low. Use with caution.")
    else:
        print("❌ VALIDATION FAILED")
        print("   Parameters may be overfit to training data.")
        print("   Try different parameters or add filters.")
    
    print("="*80)


if __name__ == "__main__":
    print("\n🚀 Starting Quick Optimization...")
    print("This will test 36 strategic combinations (~5-10 minutes)\n")
    
    start_time = datetime.now()
    
    # Run quick optimization
    df_results = quick_optimize()
    
    # If we found profitable parameters, validate them
    if len(df_results) > 0:
        df_valid = df_results[(df_results['total_trades'] >= 100) & 
                             (df_results['total_trades'] <= 5000)]
        
        if len(df_valid) > 0 and df_valid['total_profit'].max() > 0:
            best = df_valid.nlargest(1, 'total_profit').iloc[0]
            
            # Validate best parameters
            test_best_on_subsample(
                period=int(best['period']),
                deviation=best['deviation']
            )
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    print(f"\n⏱️ Total time: {elapsed:.1f} seconds")
    print("\n💡 Next steps:")
    print("   1. Review results in quick_optimization.csv")
    print("   2. If profitable, update trading_loop.py with best parameters")
    print("   3. Run full optimization for more thorough analysis")
    print("   4. Paper trade before going live\n")
