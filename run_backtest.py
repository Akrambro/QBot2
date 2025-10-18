"""
Quick Backtest Runner

Simple script to run backtests and compare all strategies.
Use this for quick testing before running full optimization.

Author: QBot2 Trading System
Version: 1.0.0
"""

from backtest_engine import BacktestEngine
import sys


def main():
    print("="*80)
    print("🚀 QBot2 Quick Backtest - All Strategies")
    print("="*80)
    
    # Initialize engine
    print("\n📊 Initializing backtest engine...")
    engine = BacktestEngine(
        data_path="data/usdjpy_100k.csv",
        payout_rate=0.85,  # 85% payout (realistic for Quotex)
        trade_amount=10.0  # $10 per trade
    )
    
    print("\n" + "="*80)
    print("🔬 RUNNING BACKTESTS")
    print("="*80)
    
    # Test 1: Breakout Strategy
    print("\n[1/3] Testing Breakout Strategy...")
    breakout_results = engine.backtest_breakout(
        lookback=30,
        start_candle=100
    )
    
    # Test 2: Engulfing Strategy
    print("\n[2/3] Testing Engulfing Strategy...")
    engulfing_results = engine.backtest_engulfing(
        lookback=30,
        start_candle=100
    )
    
    # Test 3: Bollinger Band Strategy
    print("\n[3/3] Testing Bollinger Band Strategy...")
    bollinger_results = engine.backtest_bollinger(
        period=14,
        deviation=1.0,
        lookback=30,
        start_candle=100
    )
    
    # Comparison summary
    print("\n" + "="*80)
    print("📊 STRATEGY COMPARISON")
    print("="*80)
    
    strategies = [
        ('Breakout', breakout_results),
        ('Engulfing', engulfing_results),
        ('Bollinger', bollinger_results)
    ]
    
    # Sort by total profit
    strategies.sort(key=lambda x: x[1]['total_profit'], reverse=True)
    
    print(f"\n{'Rank':<6} {'Strategy':<15} {'Trades':<10} {'Win Rate':<12} {'Profit':<12} {'PF':<8} {'Max DD':<10}")
    print("-" * 80)
    
    for rank, (name, results) in enumerate(strategies, 1):
        emoji = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉"
        print(f"{emoji} {rank:<4} {name:<15} {results['total_trades']:<10} "
              f"{results['win_rate']:<11.2f}% ${results['total_profit']:<11.2f} "
              f"{results['profit_factor']:<7.2f} ${results['max_drawdown']:<9.2f}")
    
    print("="*80)
    
    # Best strategy recommendation
    best_name, best_results = strategies[0]
    print(f"\n🏆 BEST STRATEGY: {best_name}")
    print(f"   ✓ Total Profit: ${best_results['total_profit']:.2f}")
    print(f"   ✓ Win Rate: {best_results['win_rate']:.2f}%")
    print(f"   ✓ Profit Factor: {best_results['profit_factor']:.2f}")
    print(f"   ✓ Expected Value: ${best_results['expected_value']:.2f} per trade")
    
    # Check if any strategy is profitable
    profitable_strategies = [name for name, res in strategies if res['total_profit'] > 0]
    
    if profitable_strategies:
        print(f"\n✅ {len(profitable_strategies)} profitable strateg{'y' if len(profitable_strategies) == 1 else 'ies'}")
    else:
        print("\n⚠️ WARNING: No strategies are currently profitable on this dataset!")
        print("   Consider running parameter optimization or adjusting strategy logic.")
    
    # Visualization
    print("\n📈 Generating interactive charts...")
    engine.plot_results()
    
    # Save results
    print("\n💾 Saving results...")
    engine.save_results()
    
    print("\n" + "="*80)
    print("✅ BACKTEST COMPLETE!")
    print("="*80)
    print("\nGenerated files:")
    print("  📊 backtest_results.html - Interactive visualization")
    print("  📄 backtest_results.json - Detailed metrics")
    print("\n💡 Next steps:")
    print("  - Review the interactive charts in your browser")
    print("  - Run 'python optimize_strategies.py' for parameter optimization")
    print("  - Analyze individual trades in backtest_results.json")
    print("="*80 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Backtest interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error during backtest: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
