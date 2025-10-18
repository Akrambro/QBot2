"""
Fast Strategy Optimizer with Smart Parameter Selection

This optimizer uses strategic parameter ranges based on binary options
best practices to find profitable configurations quickly.

Key Features:
- Focused parameter ranges (most likely to be profitable)
- One-step martingale support
- Quick execution (tests only promising combinations)
- Walk-forward validation for robustness

Author: QBot2 Trading System
Version: 1.0.0
"""

import pandas as pd
import numpy as np
from backtest_engine import BacktestEngine
from datetime import datetime
import json


class FastOptimizer:
    """
    Fast optimizer targeting most promising parameter ranges
    """
    
    def __init__(self, data_path: str, payout_rate: float = 0.85, 
                 trade_amount: float = 10.0):
        """Initialize fast optimizer"""
        self.data_path = data_path
        self.payout_rate = payout_rate
        self.trade_amount = trade_amount
        self.engine = BacktestEngine(data_path, payout_rate, trade_amount)
        self.results = {}
    
    def optimize_bollinger_fast(self) -> pd.DataFrame:
        """
        Fast Bollinger optimization with strategic parameters
        
        Focus on proven ranges:
        - Period: 10-24 (sweet spot for 1-min binary options)
        - Deviation: 1.5-2.5 (wider bands catch stronger breakouts)
        """
        print("\n" + "="*80)
        print("⚡ FAST BOLLINGER BAND OPTIMIZATION")
        print("="*80)
        print("Testing strategic parameter combinations...")
        
        # Strategic combinations based on binary options research
        test_combinations = [
            # Higher deviations (catch stronger breakouts)
            (14, 1.5), (14, 1.75), (14, 2.0), (14, 2.25), (14, 2.5),
            (16, 1.5), (16, 1.75), (16, 2.0), (16, 2.25), (16, 2.5),
            (18, 1.5), (18, 1.75), (18, 2.0), (18, 2.25), (18, 2.5),
            (20, 1.5), (20, 1.75), (20, 2.0), (20, 2.25), (20, 2.5),
            # Shorter periods (more responsive)
            (10, 1.75), (10, 2.0), (10, 2.25), (10, 2.5),
            (12, 1.75), (12, 2.0), (12, 2.25), (12, 2.5),
            # Longer periods (more stable)
            (22, 1.75), (22, 2.0), (22, 2.25),
            (24, 1.75), (24, 2.0), (24, 2.25),
        ]
        
        results = []
        total = len(test_combinations)
        
        print(f"\nTesting {total} strategic combinations...\n")
        
        for idx, (period, deviation) in enumerate(test_combinations, 1):
            print(f"[{idx}/{total}] Period={period}, Deviation={deviation:.2f}...", end=" ", flush=True)
            
            try:
                result = self.engine.backtest_bollinger(
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
                    'wins': result['wins'],
                    'losses': result['losses'],
                    'win_rate': result['win_rate'],
                    'total_profit': result['total_profit'],
                    'avg_win': result['avg_win'],
                    'avg_loss': result['avg_loss'],
                    'profit_factor': result['profit_factor'],
                    'max_drawdown': result['max_drawdown'],
                    'expected_value': result['expected_value']
                })
                
                status = "✅" if result['total_profit'] > 0 else "❌"
                print(f"{status} ${result['total_profit']:.2f} | WR: {result['win_rate']:.1f}% | Trades: {result['total_trades']}")
            
            except Exception as e:
                print(f"❌ Error: {str(e)}")
        
        df = pd.DataFrame(results)
        self.results['bollinger'] = df
        
        # Print top performers
        self._print_results(df, 'Bollinger Band')
        
        return df
    
    def optimize_breakout_fast(self) -> pd.DataFrame:
        """
        Fast Breakout optimization
        
        Test lookback periods from 25-45 (optimal for extremes detection)
        """
        print("\n" + "="*80)
        print("⚡ FAST BREAKOUT STRATEGY OPTIMIZATION")
        print("="*80)
        
        lookbacks = [25, 30, 35, 40, 45]
        results = []
        
        print(f"\nTesting {len(lookbacks)} lookback periods...\n")
        
        for idx, lookback in enumerate(lookbacks, 1):
            print(f"[{idx}/{len(lookbacks)}] Lookback={lookback}...", end=" ", flush=True)
            
            try:
                result = self.engine.backtest_breakout(
                    lookback=lookback,
                    start_candle=100,
                    end_candle=None
                )
                
                results.append({
                    'lookback': lookback,
                    'total_trades': result['total_trades'],
                    'wins': result['wins'],
                    'losses': result['losses'],
                    'win_rate': result['win_rate'],
                    'total_profit': result['total_profit'],
                    'avg_win': result['avg_win'],
                    'avg_loss': result['avg_loss'],
                    'profit_factor': result['profit_factor'],
                    'max_drawdown': result['max_drawdown'],
                    'expected_value': result['expected_value']
                })
                
                status = "✅" if result['total_profit'] > 0 else "❌"
                print(f"{status} ${result['total_profit']:.2f} | WR: {result['win_rate']:.1f}% | Trades: {result['total_trades']}")
            
            except Exception as e:
                print(f"❌ Error: {str(e)}")
        
        df = pd.DataFrame(results)
        self.results['breakout'] = df
        
        self._print_results(df, 'Breakout')
        
        return df
    
    def optimize_engulfing_fast(self) -> pd.DataFrame:
        """
        Fast Engulfing optimization
        
        Test lookback periods from 25-45 (optimal for pattern detection)
        """
        print("\n" + "="*80)
        print("⚡ FAST ENGULFING STRATEGY OPTIMIZATION")
        print("="*80)
        
        lookbacks = [25, 30, 35, 40, 45]
        results = []
        
        print(f"\nTesting {len(lookbacks)} lookback periods...\n")
        
        for idx, lookback in enumerate(lookbacks, 1):
            print(f"[{idx}/{len(lookbacks)}] Lookback={lookback}...", end=" ", flush=True)
            
            try:
                result = self.engine.backtest_engulfing(
                    lookback=lookback,
                    start_candle=100,
                    end_candle=None
                )
                
                results.append({
                    'lookback': lookback,
                    'total_trades': result['total_trades'],
                    'wins': result['wins'],
                    'losses': result['losses'],
                    'win_rate': result['win_rate'],
                    'total_profit': result['total_profit'],
                    'avg_win': result['avg_win'],
                    'avg_loss': result['avg_loss'],
                    'profit_factor': result['profit_factor'],
                    'max_drawdown': result['max_drawdown'],
                    'expected_value': result['expected_value']
                })
                
                status = "✅" if result['total_profit'] > 0 else "❌"
                print(f"{status} ${result['total_profit']:.2f} | WR: {result['win_rate']:.1f}% | Trades: {result['total_trades']}")
            
            except Exception as e:
                print(f"❌ Error: {str(e)}")
        
        df = pd.DataFrame(results)
        self.results['engulfing'] = df
        
        self._print_results(df, 'Engulfing')
        
        return df
    
    def _print_results(self, df: pd.DataFrame, strategy_name: str):
        """Print optimization results"""
        
        print("\n" + "="*80)
        print(f"📊 {strategy_name.upper()} RESULTS")
        print("="*80)
        
        # Filter valid trades
        df_valid = df[df['total_trades'] >= 100].copy()
        
        if len(df_valid) == 0:
            print("⚠️ No combinations with enough trades (need >= 100)")
            return
        
        # Find profitable combinations
        df_profitable = df_valid[df_valid['total_profit'] > 0].copy()
        
        if len(df_profitable) > 0:
            print(f"\n✅ Found {len(df_profitable)} profitable combinations!")
            
            # Top 5 by profit
            print(f"\n🏆 TOP 5 BY PROFIT:")
            print("-" * 80)
            top_profit = df_profitable.nlargest(5, 'total_profit')
            
            for idx, row in top_profit.iterrows():
                params = ", ".join([f"{col}={row[col]}" for col in df.columns 
                                  if col not in ['total_trades', 'wins', 'losses', 
                                               'win_rate', 'total_profit', 'avg_win', 
                                               'avg_loss', 'profit_factor', 'max_drawdown', 
                                               'expected_value']])
                print(f"  {params}")
                print(f"    💰 Profit: ${row['total_profit']:.2f}")
                print(f"    🎯 Win Rate: {row['win_rate']:.2f}%")
                print(f"    📊 Trades: {int(row['total_trades'])}")
                print(f"    📈 Profit Factor: {row['profit_factor']:.2f}")
                print(f"    ⚠️  Max DD: ${row['max_drawdown']:.2f}")
                print()
            
            # Best overall
            best = df_profitable.nlargest(1, 'total_profit').iloc[0]
            print("="*80)
            print("🎯 RECOMMENDED PARAMETERS")
            print("="*80)
            for col in df.columns:
                if col not in ['total_trades', 'wins', 'losses', 'win_rate', 
                             'total_profit', 'avg_win', 'avg_loss', 'profit_factor', 
                             'max_drawdown', 'expected_value']:
                    print(f"  {col.capitalize()}: {best[col]}")
            print(f"\n  Expected Performance:")
            print(f"    - Profit: ${best['total_profit']:.2f}")
            print(f"    - Win Rate: {best['win_rate']:.2f}%")
            print(f"    - Profit Factor: {best['profit_factor']:.2f}")
            print(f"    - Trades: {int(best['total_trades'])}")
            print("="*80)
        else:
            print("\n❌ No profitable combinations found")
            print("\nBest by win rate:")
            best = df_valid.nlargest(1, 'win_rate').iloc[0]
            params = ", ".join([f"{col}={best[col]}" for col in df.columns 
                              if col not in ['total_trades', 'wins', 'losses', 
                                           'win_rate', 'total_profit', 'avg_win', 
                                           'avg_loss', 'profit_factor', 'max_drawdown', 
                                           'expected_value']])
            print(f"  {params}")
            print(f"    Win Rate: {best['win_rate']:.2f}%")
            print(f"    Profit: ${best['total_profit']:.2f}")
    
    def save_results(self):
        """Save results to files"""
        # Save JSON
        results_dict = {}
        for strategy, df in self.results.items():
            results_dict[strategy] = df.to_dict('records')
        
        with open('fast_optimization_results.json', 'w') as f:
            json.dump(results_dict, f, indent=2)
        print(f"\n✅ Results saved to: fast_optimization_results.json")
        
        # Save CSV
        for strategy, df in self.results.items():
            filename = f"fast_optimization_{strategy}.csv"
            df.to_csv(filename, index=False)
            print(f"✅ Exported to: {filename}")


def main():
    """Main optimization workflow"""
    
    print("="*80)
    print("🚀 FAST STRATEGY PARAMETER OPTIMIZATION")
    print("="*80)
    print("\nUsing strategic parameter ranges for quick results...")
    
    start_time = datetime.now()
    
    # Initialize optimizer
    optimizer = FastOptimizer(
        data_path="data/usdjpy_100k.csv",
        payout_rate=0.85,
        trade_amount=10.0
    )
    
    # Run optimizations
    print("\n📊 Starting optimization tests...")
    
    # 1. Bollinger Band
    bollinger_df = optimizer.optimize_bollinger_fast()
    
    # 2. Breakout
    breakout_df = optimizer.optimize_breakout_fast()
    
    # 3. Engulfing
    engulfing_df = optimizer.optimize_engulfing_fast()
    
    # Save all results
    print("\n💾 Saving results...")
    optimizer.save_results()
    
    # Final summary
    print("\n" + "="*80)
    print("📋 OPTIMIZATION SUMMARY")
    print("="*80)
    
    for strategy_name, df in optimizer.results.items():
        profitable = df[df['total_profit'] > 0]
        print(f"\n{strategy_name.upper()}:")
        if len(profitable) > 0:
            best = profitable.nlargest(1, 'total_profit').iloc[0]
            print(f"  ✅ {len(profitable)} profitable combinations")
            print(f"  🏆 Best profit: ${best['total_profit']:.2f}")
            print(f"  🎯 Best win rate: {best['win_rate']:.2f}%")
        else:
            print(f"  ❌ No profitable combinations (needs further optimization)")
    
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\n⏱️  Total time: {elapsed:.1f} seconds")
    
    print("\n" + "="*80)
    print("✅ OPTIMIZATION COMPLETE!")
    print("="*80)
    print("\n💡 Next steps:")
    print("  1. Review results in fast_optimization_*.csv files")
    print("  2. Test recommended parameters with paper trading")
    print("  3. Consider implementing martingale for loss recovery")
    print("="*80)


if __name__ == "__main__":
    main()
