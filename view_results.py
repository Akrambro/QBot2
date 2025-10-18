"""
View Backtest Results

Quick viewer for backtest_results.json
"""

import json
import os


def view_results():
    """Display backtest results in terminal"""
    
    if not os.path.exists('backtest_results.json'):
        print("❌ No results found. Run 'python run_backtest.py' first.")
        return
    
    with open('backtest_results.json', 'r') as f:
        results = json.load(f)
    
    print("\n" + "="*80)
    print("📊 QBOT2 BACKTEST RESULTS SUMMARY")
    print("="*80)
    
    # Sort strategies by profit
    strategies = sorted(results.items(), key=lambda x: x[1]['total_profit'], reverse=True)
    
    for rank, (name, data) in enumerate(strategies, 1):
        emoji = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉"
        
        print(f"\n{emoji} {rank}. {data['strategy']}")
        print("-" * 80)
        print(f"   Total Trades:     {data['total_trades']:>6}")
        print(f"   Wins / Losses:    {data['wins']:>6} / {data['losses']}")
        print(f"   Win Rate:         {data['win_rate']:>6.2f}%")
        print(f"   Total Profit:     ${data['total_profit']:>9.2f}")
        print(f"   Profit Factor:    {data['profit_factor']:>6.2f}x")
        print(f"   Avg Win:          ${data['avg_win']:>9.2f}")
        print(f"   Avg Loss:         ${data['avg_loss']:>9.2f}")
        print(f"   Max Drawdown:     ${data['max_drawdown']:>9.2f} ({data['max_drawdown_pct']:.2f}%)")
        print(f"   Expected Value:   ${data['expected_value']:>9.2f} per trade")
        
        # Profitability indicator
        if data['total_profit'] > 0:
            print(f"   Status:           ✅ PROFITABLE")
        else:
            print(f"   Status:           ⚠️ UNPROFITABLE")
            
            # Calculate how much win rate needs to improve
            current_wr = data['win_rate']
            needed_wr = 54.05  # Break-even for 85% payout
            improvement = needed_wr - current_wr
            
            if improvement > 0:
                print(f"   Needs:            +{improvement:.2f}% win rate to break even")
    
    # Overall summary
    print("\n" + "="*80)
    print("📈 OVERALL STATISTICS")
    print("="*80)
    
    total_trades = sum(r['total_trades'] for r in results.values())
    total_profit = sum(r['total_profit'] for r in results.values())
    avg_win_rate = sum(r['win_rate'] for r in results.values()) / len(results)
    
    print(f"   Total Trades (All Strategies): {total_trades:,}")
    print(f"   Combined Profit:               ${total_profit:,.2f}")
    print(f"   Average Win Rate:              {avg_win_rate:.2f}%")
    print(f"   Break-Even Win Rate Needed:    54.05%")
    
    profitable_count = sum(1 for r in results.values() if r['total_profit'] > 0)
    
    if profitable_count > 0:
        print(f"\n   ✅ {profitable_count} profitable strateg{'y' if profitable_count == 1 else 'ies'}")
    else:
        print(f"\n   ⚠️ No profitable strategies yet - optimization recommended!")
    
    print("\n" + "="*80)
    print("📁 GENERATED FILES")
    print("="*80)
    
    files = [
        ('backtest_results.html', 'Interactive charts with 6 visualization panels'),
        ('backtest_results.json', 'Detailed metrics and trade-by-trade data')
    ]
    
    for filename, description in files:
        if os.path.exists(filename):
            size = os.path.getsize(filename) / 1024
            print(f"   ✅ {filename:<30} ({size:.1f} KB) - {description}")
        else:
            print(f"   ❌ {filename:<30} - Not found")
    
    print("\n" + "="*80)
    print("💡 NEXT STEPS")
    print("="*80)
    print("   1. Open backtest_results.html in browser for visual analysis")
    print("   2. Run 'python optimize_strategies.py' to find optimal parameters")
    print("   3. Test optimized parameters on out-of-sample data")
    print("   4. Paper trade best strategy before going live")
    print("="*80 + "\n")


if __name__ == "__main__":
    view_results()
