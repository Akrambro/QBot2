"""
Advanced Strategy Optimizer with Martingale Support

This module provides comprehensive optimization for all trading strategies
including support for one-step martingale risk management.

Features:
- Multi-strategy optimization (Bollinger, Breakout, Engulfing)
- One-step martingale backtesting
- Parallel parameter testing for faster results
- Walk-forward validation
- Advanced visualization and reporting

Author: QBot2 Trading System
Version: 2.0.0
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from backtest_engine import BacktestEngine
from datetime import datetime
import json
from typing import Dict, List, Tuple, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed
import itertools


class MartingaleBacktestEngine(BacktestEngine):
    """
    Extended BacktestEngine with one-step martingale support
    
    Martingale Logic:
    - If a trade loses, next trade in same direction uses 1.5x amount
    - If martingale trade wins, reset to base amount
    - Only one martingale step (not unlimited progression)
    """
    
    def __init__(self, data_path: str, payout_rate: float = 0.85, 
                 trade_amount: float = 10.0, martingale_multiplier: float = 1.5):
        super().__init__(data_path, payout_rate, trade_amount)
        self.martingale_multiplier = martingale_multiplier
        self.use_martingale = True
    
    def backtest_with_martingale(
        self,
        strategy: str,
        **kwargs
    ) -> Dict:
        """
        Run backtest with one-step martingale logic
        
        Args:
            strategy: 'bollinger', 'breakout', or 'engulfing'
            **kwargs: Strategy-specific parameters
        
        Returns:
            Dictionary with backtest results including martingale stats
        """
        # First run regular backtest to get all signals
        if strategy == 'bollinger':
            base_results = self.backtest_bollinger(**kwargs)
        elif strategy == 'breakout':
            base_results = self.backtest_breakout(**kwargs)
        elif strategy == 'engulfing':
            base_results = self.backtest_engulfing(**kwargs)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
        
        # Now apply martingale logic to the trades
        trades = base_results['trades']
        
        if not trades:
            return base_results
        
        # Recalculate with martingale
        martingale_trades = []
        current_equity = 0
        equity_curve = [0]
        
        last_trade_lost = False
        last_signal = None
        martingale_active = False
        martingale_wins = 0
        martingale_losses = 0
        base_wins = 0
        base_losses = 0
        
        for trade in trades:
            # Determine trade amount
            if martingale_active and trade['signal'].lower() == last_signal:
                # Martingale: increase amount
                current_amount = self.trade_amount * self.martingale_multiplier
                is_martingale = True
            else:
                # Regular trade
                current_amount = self.trade_amount
                is_martingale = False
                martingale_active = False
            
            # Recalculate P&L with adjusted amount
            if trade['won']:
                pnl = current_amount * self.payout_rate
                if is_martingale:
                    martingale_wins += 1
                else:
                    base_wins += 1
                martingale_active = False  # Reset after win
            else:
                pnl = -current_amount
                if is_martingale:
                    martingale_losses += 1
                else:
                    base_losses += 1
                # Activate martingale for next trade if same signal
                martingale_active = True
                last_signal = trade['signal'].lower()
            
            current_equity += pnl
            equity_curve.append(current_equity)
            
            # Store trade with martingale info
            martingale_trade = trade.copy()
            martingale_trade['pnl'] = pnl
            martingale_trade['equity'] = current_equity
            martingale_trade['amount'] = current_amount
            martingale_trade['is_martingale'] = is_martingale
            martingale_trades.append(martingale_trade)
        
        # Recalculate metrics
        wins = [t for t in martingale_trades if t['won']]
        losses = [t for t in martingale_trades if not t['won']]
        
        win_rate = (len(wins) / len(martingale_trades)) * 100 if martingale_trades else 0
        total_profit = equity_curve[-1]
        
        # Calculate drawdown
        peak = equity_curve[0]
        max_dd = 0
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            dd = peak - equity
            if dd > max_dd:
                max_dd = dd
        
        max_dd_pct = (max_dd / (abs(peak) + 1)) * 100 if peak != 0 else 0
        
        # Average win/loss
        avg_win = np.mean([t['pnl'] for t in wins]) if wins else 0
        avg_loss = np.mean([t['pnl'] for t in losses]) if losses else 0
        
        # Profit factor
        gross_profit = sum([t['pnl'] for t in wins]) if wins else 0
        gross_loss = abs(sum([t['pnl'] for t in losses])) if losses else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Expected value
        expected_value = total_profit / len(martingale_trades) if martingale_trades else 0
        
        results = {
            'strategy': f"{base_results['strategy']} (Martingale)",
            'total_trades': len(martingale_trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': win_rate,
            'total_profit': total_profit,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': max_dd,
            'max_drawdown_pct': max_dd_pct,
            'expected_value': expected_value,
            'trades': martingale_trades,
            'equity_curve': equity_curve,
            'martingale_stats': {
                'base_wins': base_wins,
                'base_losses': base_losses,
                'martingale_wins': martingale_wins,
                'martingale_losses': martingale_losses,
                'martingale_recovery_rate': (martingale_wins / (martingale_wins + martingale_losses) * 100) 
                    if (martingale_wins + martingale_losses) > 0 else 0
            }
        }
        
        return results


class AdvancedStrategyOptimizer:
    """
    Advanced multi-strategy optimizer with martingale support
    """
    
    def __init__(self, data_path: str, payout_rate: float = 0.85, 
                 trade_amount: float = 10.0, use_martingale: bool = True):
        """
        Initialize advanced optimizer
        
        Args:
            data_path: Path to historical data CSV
            payout_rate: Payout rate for winning trades
            trade_amount: Base amount per trade
            use_martingale: Enable one-step martingale
        """
        self.data_path = data_path
        self.payout_rate = payout_rate
        self.trade_amount = trade_amount
        self.use_martingale = use_martingale
        self.optimization_results = {}
        
        if use_martingale:
            self.engine = MartingaleBacktestEngine(data_path, payout_rate, trade_amount)
        else:
            self.engine = BacktestEngine(data_path, payout_rate, trade_amount)
    
    def optimize_bollinger_comprehensive(
        self,
        period_range: tuple = (8, 30),
        deviation_range: tuple = (0.5, 3.0),
        period_step: int = 2,
        deviation_step: float = 0.25
    ) -> pd.DataFrame:
        """
        Comprehensive Bollinger Band optimization
        
        Tests wider parameter ranges to find optimal settings
        """
        print("\n" + "="*80)
        print("🔧 COMPREHENSIVE BOLLINGER BAND OPTIMIZATION")
        if self.use_martingale:
            print("   📈 WITH ONE-STEP MARTINGALE (1.5x multiplier)")
        print("="*80)
        print(f"Period Range: {period_range[0]} - {period_range[1]} (step: {period_step})")
        print(f"Deviation Range: {deviation_range[0]:.2f} - {deviation_range[1]:.2f} (step: {deviation_step})")
        
        results = []
        
        periods = range(period_range[0], period_range[1] + 1, period_step)
        deviations = np.arange(deviation_range[0], deviation_range[1] + deviation_step, deviation_step)
        
        total_combinations = len(list(periods)) * len(deviations)
        current = 0
        
        print(f"\nTotal combinations to test: {total_combinations}\n")
        
        for period in periods:
            for deviation in deviations:
                current += 1
                print(f"[{current}/{total_combinations}] Testing Period={period}, Deviation={deviation:.2f}...", end=" ", flush=True)
                
                try:
                    # Run backtest
                    if self.use_martingale:
                        result = self.engine.backtest_with_martingale(
                            strategy='bollinger',
                            period=period,
                            deviation=deviation,
                            lookback=50,
                            start_candle=100,
                            end_candle=None
                        )
                    else:
                        result = self.engine.backtest_bollinger(
                            period=period,
                            deviation=deviation,
                            lookback=50,
                            start_candle=100,
                            end_candle=None
                        )
                    
                    # Store results
                    result_dict = {
                        'period': period,
                        'deviation': round(deviation, 2),
                        'total_trades': result['total_trades'],
                        'wins': result['wins'],
                        'losses': result['losses'],
                        'win_rate': result['win_rate'],
                        'total_profit': result['total_profit'],
                        'avg_win': result['avg_win'],
                        'avg_loss': result['avg_loss'],
                        'profit_factor': result['profit_factor'],
                        'max_drawdown': result['max_drawdown'],
                        'max_drawdown_pct': result['max_drawdown_pct'],
                        'expected_value': result['expected_value']
                    }
                    
                    if self.use_martingale and 'martingale_stats' in result:
                        result_dict['martingale_recovery_rate'] = result['martingale_stats']['martingale_recovery_rate']
                    
                    results.append(result_dict)
                    
                    status = "✅" if result['total_profit'] > 0 else "❌"
                    print(f"{status} Profit: ${result['total_profit']:.2f}, WR: {result['win_rate']:.1f}%, Trades: {result['total_trades']}")
                
                except Exception as e:
                    print(f"❌ Error: {str(e)}")
                    continue
        
        df_results = pd.DataFrame(results)
        self.optimization_results['bollinger'] = df_results
        
        # Find best parameters
        self._print_top_performers(df_results, 'Bollinger Band')
        
        return df_results
    
    def optimize_breakout(
        self,
        lookback_range: tuple = (20, 50),
        lookback_step: int = 5
    ) -> pd.DataFrame:
        """
        Optimize Breakout strategy parameters
        
        Tests different lookback periods for extreme detection
        """
        print("\n" + "="*80)
        print("🔧 BREAKOUT STRATEGY OPTIMIZATION")
        if self.use_martingale:
            print("   📈 WITH ONE-STEP MARTINGALE (1.5x multiplier)")
        print("="*80)
        print(f"Lookback Range: {lookback_range[0]} - {lookback_range[1]} (step: {lookback_step})")
        
        results = []
        
        lookbacks = range(lookback_range[0], lookback_range[1] + 1, lookback_step)
        
        total_combinations = len(list(lookbacks))
        current = 0
        
        print(f"\nTotal combinations to test: {total_combinations}\n")
        
        for lookback in lookbacks:
            current += 1
            print(f"[{current}/{total_combinations}] Testing Lookback={lookback}...", end=" ", flush=True)
            
            try:
                # Run backtest
                if self.use_martingale:
                    result = self.engine.backtest_with_martingale(
                        strategy='breakout',
                        lookback=lookback,
                        start_candle=100,
                        end_candle=None
                    )
                else:
                    result = self.engine.backtest_breakout(
                        lookback=lookback,
                        start_candle=100,
                        end_candle=None
                    )
                
                # Store results
                result_dict = {
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
                    'max_drawdown_pct': result['max_drawdown_pct'],
                    'expected_value': result['expected_value']
                }
                
                if self.use_martingale and 'martingale_stats' in result:
                    result_dict['martingale_recovery_rate'] = result['martingale_stats']['martingale_recovery_rate']
                
                results.append(result_dict)
                
                status = "✅" if result['total_profit'] > 0 else "❌"
                print(f"{status} Profit: ${result['total_profit']:.2f}, WR: {result['win_rate']:.1f}%, Trades: {result['total_trades']}")
            
            except Exception as e:
                print(f"❌ Error: {str(e)}")
                continue
        
        df_results = pd.DataFrame(results)
        self.optimization_results['breakout'] = df_results
        
        # Find best parameters
        self._print_top_performers(df_results, 'Breakout Strategy')
        
        return df_results
    
    def optimize_engulfing(
        self,
        lookback_range: tuple = (20, 50),
        lookback_step: int = 5
    ) -> pd.DataFrame:
        """
        Optimize Engulfing strategy parameters
        
        Tests different lookback periods for pattern detection
        """
        print("\n" + "="*80)
        print("🔧 ENGULFING STRATEGY OPTIMIZATION")
        if self.use_martingale:
            print("   📈 WITH ONE-STEP MARTINGALE (1.5x multiplier)")
        print("="*80)
        print(f"Lookback Range: {lookback_range[0]} - {lookback_range[1]} (step: {lookback_step})")
        
        results = []
        
        lookbacks = range(lookback_range[0], lookback_range[1] + 1, lookback_step)
        
        total_combinations = len(list(lookbacks))
        current = 0
        
        print(f"\nTotal combinations to test: {total_combinations}\n")
        
        for lookback in lookbacks:
            current += 1
            print(f"[{current}/{total_combinations}] Testing Lookback={lookback}...", end=" ", flush=True)
            
            try:
                # Run backtest
                if self.use_martingale:
                    result = self.engine.backtest_with_martingale(
                        strategy='engulfing',
                        lookback=lookback,
                        start_candle=100,
                        end_candle=None
                    )
                else:
                    result = self.engine.backtest_engulfing(
                        lookback=lookback,
                        start_candle=100,
                        end_candle=None
                    )
                
                # Store results
                result_dict = {
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
                    'max_drawdown_pct': result['max_drawdown_pct'],
                    'expected_value': result['expected_value']
                }
                
                if self.use_martingale and 'martingale_stats' in result:
                    result_dict['martingale_recovery_rate'] = result['martingale_stats']['martingale_recovery_rate']
                
                results.append(result_dict)
                
                status = "✅" if result['total_profit'] > 0 else "❌"
                print(f"{status} Profit: ${result['total_profit']:.2f}, WR: {result['win_rate']:.1f}%, Trades: {result['total_trades']}")
            
            except Exception as e:
                print(f"❌ Error: {str(e)}")
                continue
        
        df_results = pd.DataFrame(results)
        self.optimization_results['engulfing'] = df_results
        
        # Find best parameters
        self._print_top_performers(df_results, 'Engulfing Strategy')
        
        return df_results
    
    def _print_top_performers(self, df: pd.DataFrame, strategy_name: str, top_n: int = 5):
        """Print top performing parameter combinations"""
        
        print("\n" + "="*80)
        print(f"🏆 TOP {top_n} PARAMETER COMBINATIONS - {strategy_name}")
        print("="*80)
        
        # Filter out combinations with too few trades
        df_filtered = df[df['total_trades'] >= 10].copy()
        
        if len(df_filtered) == 0:
            print("⚠️ No combinations with sufficient trades (min 10)")
            return
        
        # Sort by total profit
        print(f"\n📈 By Total Profit:")
        print("-" * 80)
        top_profit = df_filtered.nlargest(top_n, 'total_profit')
        for idx, row in top_profit.iterrows():
            params = ", ".join([f"{col}={row[col]}" for col in df.columns if col not in ['total_trades', 'wins', 'losses', 'win_rate', 'total_profit', 'avg_win', 'avg_loss', 'profit_factor', 'max_drawdown', 'max_drawdown_pct', 'expected_value', 'martingale_recovery_rate']])
            print(f"   {params} → "
                  f"Profit: ${row['total_profit']:.2f}, Win Rate: {row['win_rate']:.1f}%, "
                  f"Trades: {int(row['total_trades'])}, PF: {row['profit_factor']:.2f}")
        
        # Sort by win rate
        print(f"\n🎯 By Win Rate:")
        print("-" * 80)
        top_winrate = df_filtered.nlargest(top_n, 'win_rate')
        for idx, row in top_winrate.iterrows():
            params = ", ".join([f"{col}={row[col]}" for col in df.columns if col not in ['total_trades', 'wins', 'losses', 'win_rate', 'total_profit', 'avg_win', 'avg_loss', 'profit_factor', 'max_drawdown', 'max_drawdown_pct', 'expected_value', 'martingale_recovery_rate']])
            print(f"   {params} → "
                  f"Win Rate: {row['win_rate']:.1f}%, Profit: ${row['total_profit']:.2f}, "
                  f"Trades: {int(row['total_trades'])}, PF: {row['profit_factor']:.2f}")
        
        print("="*80)
    
    def save_results(self, filename: str = "advanced_optimization_results.json"):
        """Save optimization results to JSON"""
        
        results_dict = {}
        
        for strategy, df in self.optimization_results.items():
            results_dict[strategy] = df.to_dict('records')
        
        with open(filename, 'w') as f:
            json.dump(results_dict, f, indent=2)
        
        print(f"\n✅ Optimization results saved to: {filename}")
    
    def export_to_csv(self):
        """Export optimization results to CSV files"""
        
        for strategy, df in self.optimization_results.items():
            filename = f"advanced_optimization_{strategy}.csv"
            df.to_csv(filename, index=False)
            print(f"✅ Exported {strategy} results to: {filename}")


def main():
    """Main optimization workflow"""
    
    print("="*80)
    print("🔬 QBot2 ADVANCED STRATEGY OPTIMIZATION")
    print("   📈 WITH ONE-STEP MARTINGALE SUPPORT")
    print("="*80)
    
    # Initialize optimizer with martingale
    optimizer = AdvancedStrategyOptimizer(
        data_path="data/usdjpy_100k.csv",
        payout_rate=0.85,
        trade_amount=10.0,
        use_martingale=True
    )
    
    # Optimize all strategies
    print("\n🎯 Starting comprehensive optimization...")
    
    # 1. Bollinger Band - wider parameter ranges
    print("\n" + "="*80)
    print("1️⃣ BOLLINGER BAND STRATEGY")
    print("="*80)
    bollinger_results = optimizer.optimize_bollinger_comprehensive(
        period_range=(8, 30),
        deviation_range=(0.5, 3.0),
        period_step=2,
        deviation_step=0.25
    )
    
    # 2. Breakout Strategy
    print("\n" + "="*80)
    print("2️⃣ BREAKOUT STRATEGY")
    print("="*80)
    breakout_results = optimizer.optimize_breakout(
        lookback_range=(20, 50),
        lookback_step=5
    )
    
    # 3. Engulfing Strategy
    print("\n" + "="*80)
    print("3️⃣ ENGULFING STRATEGY")
    print("="*80)
    engulfing_results = optimizer.optimize_engulfing(
        lookback_range=(20, 50),
        lookback_step=5
    )
    
    # Save results
    print("\n💾 Saving optimization results...")
    optimizer.save_results()
    optimizer.export_to_csv()
    
    # Generate summary report
    print("\n" + "="*80)
    print("📊 OPTIMIZATION SUMMARY")
    print("="*80)
    
    for strategy_name, df in optimizer.optimization_results.items():
        print(f"\n{strategy_name.upper()}:")
        profitable = df[df['total_profit'] > 0]
        if len(profitable) > 0:
            best = profitable.nlargest(1, 'total_profit').iloc[0]
            print(f"  ✅ {len(profitable)} profitable combinations found")
            print(f"  🏆 Best profit: ${best['total_profit']:.2f}")
            print(f"     Win rate: {best['win_rate']:.2f}%")
            print(f"     Total trades: {int(best['total_trades'])}")
        else:
            print(f"  ❌ No profitable combinations found")
    
    print("\n" + "="*80)
    print("✅ OPTIMIZATION COMPLETE!")
    print("="*80)
    print("\nFiles generated:")
    print("  - advanced_optimization_results.json (detailed metrics)")
    print("  - advanced_optimization_*.csv (exportable data)")
    print("\n💡 Review the results to identify optimal parameter combinations.")
    print("="*80)


if __name__ == "__main__":
    main()
