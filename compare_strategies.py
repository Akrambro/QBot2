"""
Test Mean Reversion vs Breakout Strategy

This script compares the performance of mean reversion vs breakout
approaches for Bollinger Band trading on 1-minute binary options.
"""

from backtest_engine import BacktestEngine
import json

def compare_strategies():
    """Compare mean reversion vs breakout strategies"""
    
    print("="*80)
    print("📊 MEAN REVERSION VS BREAKOUT COMPARISON")
    print("="*80)
    print("\nTesting on 100k candles of USDJPY 1-minute data...")
    
    # Initialize engine
    engine = BacktestEngine(
        data_path="data/usdjpy_100k.csv",
        payout_rate=0.85,
        trade_amount=10.0
    )
    
    results = {}
    
    # Test 1: Mean Reversion with optimized parameters
    print("\n" + "="*80)
    print("1️⃣ BOLLINGER MEAN REVERSION (Period=20, Deviation=2.0)")
    print("="*80)
    print("Strategy: Trade REVERSALS at band extremes")
    print("  - CALL when price breaks BELOW lower band (expecting bounce)")
    print("  - PUT when price breaks ABOVE upper band (expecting pullback)")
    
    mr_result = engine.backtest_bollinger(
        period=20,
        deviation=2.0,
        lookback=50,
        start_candle=100,
        end_candle=None,
        mean_reversion=True
    )
    
    results['mean_reversion'] = {
        'strategy': 'Mean Reversion',
        'period': 20,
        'deviation': 2.0,
        'total_trades': mr_result['total_trades'],
        'wins': mr_result['wins'],
        'losses': mr_result['losses'],
        'win_rate': mr_result['win_rate'],
        'total_profit': mr_result['total_profit'],
        'profit_factor': mr_result['profit_factor'],
        'expected_value': mr_result['expected_value'],
        'max_drawdown': mr_result['max_drawdown']
    }
    
    # Test 2: Breakout with optimized parameters
    print("\n" + "="*80)
    print("2️⃣ BOLLINGER BREAKOUT (Period=20, Deviation=2.0)")
    print("="*80)
    print("Strategy: Trade BREAKOUTS at band extremes")
    print("  - CALL when price breaks ABOVE upper band (momentum)")
    print("  - PUT when price breaks BELOW lower band (momentum)")
    
    bo_result = engine.backtest_bollinger(
        period=20,
        deviation=2.0,
        lookback=50,
        start_candle=100,
        end_candle=None,
        mean_reversion=False
    )
    
    results['breakout'] = {
        'strategy': 'Breakout',
        'period': 20,
        'deviation': 2.0,
        'total_trades': bo_result['total_trades'],
        'wins': bo_result['wins'],
        'losses': bo_result['losses'],
        'win_rate': bo_result['win_rate'],
        'total_profit': bo_result['total_profit'],
        'profit_factor': bo_result['profit_factor'],
        'expected_value': bo_result['expected_value'],
        'max_drawdown': bo_result['max_drawdown']
    }
    
    # Comparison Table
    print("\n" + "="*80)
    print("📊 DETAILED COMPARISON")
    print("="*80)
    
    print(f"\n{'Metric':<25} {'Mean Reversion':<20} {'Breakout':<20} {'Winner':<15}")
    print("-" * 80)
    
    metrics = [
        ('Total Trades', 'total_trades', 'higher'),
        ('Win Rate (%)', 'win_rate', 'higher'),
        ('Total Profit ($)', 'total_profit', 'higher'),
        ('Profit Factor', 'profit_factor', 'higher'),
        ('Expected Value', 'expected_value', 'higher'),
        ('Max Drawdown ($)', 'max_drawdown', 'lower'),
    ]
    
    mr_wins = 0
    bo_wins = 0
    
    for metric_name, metric_key, better in metrics:
        mr_val = results['mean_reversion'][metric_key]
        bo_val = results['breakout'][metric_key]
        
        if better == 'higher':
            winner = 'Mean Reversion' if mr_val > bo_val else 'Breakout'
            if mr_val > bo_val:
                mr_wins += 1
            else:
                bo_wins += 1
        else:  # lower is better
            winner = 'Mean Reversion' if mr_val < bo_val else 'Breakout'
            if mr_val < bo_val:
                mr_wins += 1
            else:
                bo_wins += 1
        
        # Format values
        if 'Rate' in metric_name or 'Factor' in metric_name or 'Value' in metric_name:
            mr_str = f"{mr_val:.2f}"
            bo_str = f"{bo_val:.2f}"
        else:
            mr_str = f"{int(mr_val)}" if metric_name == 'Total Trades' else f"{mr_val:.2f}"
            bo_str = f"{int(bo_val)}" if metric_name == 'Total Trades' else f"{bo_val:.2f}"
        
        winner_emoji = "🏆" if winner == 'Mean Reversion' else "📉" if winner == 'Breakout' else "="
        print(f"{metric_name:<25} {mr_str:<20} {bo_str:<20} {winner_emoji} {winner}")
    
    # Final Verdict
    print("\n" + "="*80)
    print("🏁 FINAL VERDICT")
    print("="*80)
    
    mr_profit = results['mean_reversion']['total_profit']
    bo_profit = results['breakout']['total_profit']
    mr_wr = results['mean_reversion']['win_rate']
    bo_wr = results['breakout']['win_rate']
    
    print(f"\nMean Reversion: {mr_wins} metrics won")
    print(f"Breakout: {bo_wins} metrics won")
    
    if mr_profit > 0 and bo_profit > 0:
        if mr_profit > bo_profit:
            print(f"\n✅ WINNER: Mean Reversion")
            print(f"   Profit advantage: ${mr_profit - bo_profit:.2f}")
            print(f"   Win rate advantage: {mr_wr - bo_wr:+.2f}%")
        else:
            print(f"\n✅ WINNER: Breakout")
            print(f"   Profit advantage: ${bo_profit - mr_profit:.2f}")
            print(f"   Win rate advantage: {bo_wr - mr_wr:+.2f}%")
    elif mr_profit > 0:
        print(f"\n✅ CLEAR WINNER: Mean Reversion (Only profitable strategy)")
        print(f"   Profit: ${mr_profit:.2f}")
        print(f"   Win Rate: {mr_wr:.2f}%")
    elif bo_profit > 0:
        print(f"\n✅ CLEAR WINNER: Breakout (Only profitable strategy)")
        print(f"   Profit: ${bo_profit:.2f}")
        print(f"   Win Rate: {bo_wr:.2f}%")
    else:
        print(f"\n⚠️  BOTH STRATEGIES UNPROFITABLE")
        if mr_profit > bo_profit:
            print(f"   Less bad: Mean Reversion (${mr_profit:.2f} vs ${bo_profit:.2f})")
        else:
            print(f"   Less bad: Breakout (${bo_profit:.2f} vs ${mr_profit:.2f})")
    
    # Profitability Analysis
    print("\n" + "="*80)
    print("💰 PROFITABILITY ANALYSIS")
    print("="*80)
    print(f"\nBreak-even win rate (85% payout): 54.05%")
    print(f"\nMean Reversion: {mr_wr:.2f}%", end="")
    if mr_wr >= 54.05:
        print(f" ✅ PROFITABLE ({mr_wr - 54.05:.2f}% above threshold)")
    else:
        print(f" ❌ Not profitable (need {54.05 - mr_wr:.2f}% more)")
    
    print(f"Breakout: {bo_wr:.2f}%", end="")
    if bo_wr >= 54.05:
        print(f" ✅ PROFITABLE ({bo_wr - 54.05:.2f}% above threshold)")
    else:
        print(f" ❌ Not profitable (need {54.05 - bo_wr:.2f}% more)")
    
    # Save results
    with open('strategy_comparison_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\n✅ Results saved to: strategy_comparison_results.json")
    
    # Recommendation
    print("\n" + "="*80)
    print("💡 RECOMMENDATION")
    print("="*80)
    
    if mr_profit > bo_profit and mr_wr > bo_wr:
        print("\n🎯 Use MEAN REVERSION strategy")
        print("   Reasons:")
        print(f"   - Better win rate ({mr_wr:.2f}% vs {bo_wr:.2f}%)")
        print(f"   - Better profit (${mr_profit:.2f} vs ${bo_profit:.2f})")
        print("   - Aligns with 1-minute market behavior (mean reversion)")
    elif bo_profit > mr_profit and bo_wr > mr_wr:
        print("\n🎯 Use BREAKOUT strategy")
        print("   Reasons:")
        print(f"   - Better win rate ({bo_wr:.2f}% vs {mr_wr:.2f}%)")
        print(f"   - Better profit (${bo_profit:.2f} vs ${mr_profit:.2f})")
    else:
        print("\n⚠️  Neither strategy is clearly superior")
        print("   Suggestions:")
        print("   1. Consider combining both strategies with filters")
        print("   2. Add additional confirmation indicators (RSI, Volume)")
        print("   3. Implement martingale for loss recovery")
        print("   4. Test on different currency pairs and timeframes")
    
    print("="*80)


if __name__ == "__main__":
    compare_strategies()
