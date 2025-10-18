"""
Strategy Parameter Optimization

Systematically tests parameter combinations to find optimal settings
for each trading strategy.

Optimization Targets:
- Bollinger Band: period, deviation
- Breakout: (future optimization)
- Engulfing: (future optimization)

Author: QBot2 Trading System
Version: 1.0.0
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from backtest_engine import BacktestEngine
from datetime import datetime
import json


class StrategyOptimizer:
    """
    Parameter optimization for trading strategies
    """
    
    def __init__(self, data_path: str, payout_rate: float = 0.85, trade_amount: float = 10.0):
        """
        Initialize optimizer
        
        Args:
            data_path: Path to historical data CSV
            payout_rate: Payout rate for winning trades
            trade_amount: Amount per trade
        """
        self.engine = BacktestEngine(data_path, payout_rate, trade_amount)
        self.optimization_results = {}
    
    def optimize_bollinger(
        self,
        period_range: tuple = (10, 25),
        deviation_range: tuple = (0.5, 2.5),
        period_step: int = 1,
        deviation_step: float = 0.25
    ) -> pd.DataFrame:
        """
        Grid search optimization for Bollinger Band strategy
        
        Args:
            period_range: (min, max) period values
            deviation_range: (min, max) deviation values
            period_step: Increment for period
            deviation_step: Increment for deviation
            
        Returns:
            DataFrame with all parameter combinations and metrics
        """
        print("\n" + "="*80)
        print("🔧 BOLLINGER BAND PARAMETER OPTIMIZATION")
        print("="*80)
        print(f"Period Range: {period_range[0]} - {period_range[1]} (step: {period_step})")
        print(f"Deviation Range: {deviation_range[0]:.2f} - {deviation_range[1]:.2f} (step: {deviation_step})")
        
        results = []
        
        periods = range(period_range[0], period_range[1] + 1, period_step)
        deviations = np.arange(deviation_range[0], deviation_range[1] + deviation_step, deviation_step)
        
        total_combinations = len(periods) * len(deviations)
        current = 0
        
        print(f"\nTotal combinations to test: {total_combinations}\n")
        
        for period in periods:
            for deviation in deviations:
                current += 1
                print(f"[{current}/{total_combinations}] Testing Period={period}, Deviation={deviation:.2f}...", end=" ")
                
                # Run backtest
                result = self.engine.backtest_bollinger(
                    period=period,
                    deviation=deviation,
                    lookback=50,
                    start_candle=100,
                    end_candle=None
                )
                
                # Store results
                results.append({
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
                })
                
                print(f"✓ Profit: ${result['total_profit']:.2f}, Win Rate: {result['win_rate']:.1f}%, Trades: {result['total_trades']}")
        
        df_results = pd.DataFrame(results)
        self.optimization_results['bollinger'] = df_results
        
        # Find best by different metrics
        self._print_top_performers(df_results, 'Bollinger Band')
        
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
            print(f"   Period={int(row['period'])}, Dev={row['deviation']:.2f} → "
                  f"Profit: ${row['total_profit']:.2f}, Win Rate: {row['win_rate']:.1f}%, "
                  f"Trades: {int(row['total_trades'])}, PF: {row['profit_factor']:.2f}")
        
        # Sort by win rate
        print(f"\n🎯 By Win Rate:")
        print("-" * 80)
        top_winrate = df_filtered.nlargest(top_n, 'win_rate')
        for idx, row in top_winrate.iterrows():
            print(f"   Period={int(row['period'])}, Dev={row['deviation']:.2f} → "
                  f"Win Rate: {row['win_rate']:.1f}%, Profit: ${row['total_profit']:.2f}, "
                  f"Trades: {int(row['total_trades'])}, PF: {row['profit_factor']:.2f}")
        
        # Sort by profit factor
        print(f"\n💪 By Profit Factor:")
        print("-" * 80)
        top_pf = df_filtered.nlargest(top_n, 'profit_factor')
        for idx, row in top_pf.iterrows():
            print(f"   Period={int(row['period'])}, Dev={row['deviation']:.2f} → "
                  f"PF: {row['profit_factor']:.2f}, Profit: ${row['total_profit']:.2f}, "
                  f"Win Rate: {row['win_rate']:.1f}%, Trades: {int(row['total_trades'])}")
        
        # Sort by expected value
        print(f"\n💰 By Expected Value per Trade:")
        print("-" * 80)
        top_ev = df_filtered.nlargest(top_n, 'expected_value')
        for idx, row in top_ev.iterrows():
            print(f"   Period={int(row['period'])}, Dev={row['deviation']:.2f} → "
                  f"EV: ${row['expected_value']:.2f}, Profit: ${row['total_profit']:.2f}, "
                  f"Win Rate: {row['win_rate']:.1f}%, Trades: {int(row['total_trades'])}")
        
        print("="*80)
    
    def plot_bollinger_optimization(self):
        """Create heatmaps for Bollinger Band optimization results"""
        
        if 'bollinger' not in self.optimization_results:
            print("⚠️ No Bollinger optimization results to plot")
            return
        
        df = self.optimization_results['bollinger']
        
        # Create pivot tables for heatmaps
        pivot_profit = df.pivot_table(
            values='total_profit',
            index='deviation',
            columns='period',
            aggfunc='mean'
        )
        
        pivot_winrate = df.pivot_table(
            values='win_rate',
            index='deviation',
            columns='period',
            aggfunc='mean'
        )
        
        pivot_pf = df.pivot_table(
            values='profit_factor',
            index='deviation',
            columns='period',
            aggfunc='mean'
        )
        
        pivot_trades = df.pivot_table(
            values='total_trades',
            index='deviation',
            columns='period',
            aggfunc='mean'
        )
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Total Profit ($)',
                'Win Rate (%)',
                'Profit Factor',
                'Total Trades'
            ),
            specs=[[{"type": "heatmap"}, {"type": "heatmap"}],
                   [{"type": "heatmap"}, {"type": "heatmap"}]]
        )
        
        # Heatmap 1: Total Profit
        fig.add_trace(
            go.Heatmap(
                z=pivot_profit.values,
                x=pivot_profit.columns,
                y=pivot_profit.index,
                colorscale='RdYlGn',
                text=pivot_profit.values,
                texttemplate='$%{text:.0f}',
                colorbar=dict(x=0.45, y=0.75, len=0.4)
            ),
            row=1, col=1
        )
        
        # Heatmap 2: Win Rate
        fig.add_trace(
            go.Heatmap(
                z=pivot_winrate.values,
                x=pivot_winrate.columns,
                y=pivot_winrate.index,
                colorscale='Blues',
                text=pivot_winrate.values,
                texttemplate='%{text:.1f}%',
                colorbar=dict(x=1.0, y=0.75, len=0.4)
            ),
            row=1, col=2
        )
        
        # Heatmap 3: Profit Factor
        fig.add_trace(
            go.Heatmap(
                z=pivot_pf.values,
                x=pivot_pf.columns,
                y=pivot_pf.index,
                colorscale='Viridis',
                text=pivot_pf.values,
                texttemplate='%{text:.2f}',
                colorbar=dict(x=0.45, y=0.25, len=0.4)
            ),
            row=2, col=1
        )
        
        # Heatmap 4: Total Trades
        fig.add_trace(
            go.Heatmap(
                z=pivot_trades.values,
                x=pivot_trades.columns,
                y=pivot_trades.index,
                colorscale='Oranges',
                text=pivot_trades.values,
                texttemplate='%{text:.0f}',
                colorbar=dict(x=1.0, y=0.25, len=0.4)
            ),
            row=2, col=2
        )
        
        # Update axes
        fig.update_xaxes(title_text="Period", row=1, col=1)
        fig.update_yaxes(title_text="Deviation", row=1, col=1)
        
        fig.update_xaxes(title_text="Period", row=1, col=2)
        fig.update_yaxes(title_text="Deviation", row=1, col=2)
        
        fig.update_xaxes(title_text="Period", row=2, col=1)
        fig.update_yaxes(title_text="Deviation", row=2, col=1)
        
        fig.update_xaxes(title_text="Period", row=2, col=2)
        fig.update_yaxes(title_text="Deviation", row=2, col=2)
        
        # Update layout
        fig.update_layout(
            title_text="Bollinger Band Strategy - Parameter Optimization Heatmaps",
            height=900,
            showlegend=False,
            template='plotly_dark'
        )
        
        # Save and show
        output_file = "bollinger_optimization_heatmap.html"
        fig.write_html(output_file)
        print(f"\n✅ Heatmap saved to: {output_file}")
        fig.show()
    
    def save_optimization_results(self, filename: str = "optimization_results.json"):
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
            filename = f"optimization_{strategy}.csv"
            df.to_csv(filename, index=False)
            print(f"✅ Exported {strategy} results to: {filename}")


def main():
    """Main optimization workflow"""
    
    print("="*80)
    print("🔬 QBot2 Strategy Parameter Optimization")
    print("="*80)
    
    # Initialize optimizer
    optimizer = StrategyOptimizer(
        data_path="data/usdjpy_100k.csv",
        payout_rate=0.85,
        trade_amount=10.0
    )
    
    # Optimize Bollinger Band strategy
    print("\n🎯 Starting Bollinger Band optimization...")
    bollinger_results = optimizer.optimize_bollinger(
        period_range=(10, 25),
        deviation_range=(0.5, 2.5),
        period_step=1,
        deviation_step=0.25
    )
    
    # Create visualizations
    print("\n📊 Creating optimization heatmaps...")
    optimizer.plot_bollinger_optimization()
    
    # Save results
    print("\n💾 Saving optimization results...")
    optimizer.save_optimization_results()
    optimizer.export_to_csv()
    
    print("\n" + "="*80)
    print("✅ OPTIMIZATION COMPLETE!")
    print("="*80)
    print("\nFiles generated:")
    print("  - bollinger_optimization_heatmap.html (interactive visualization)")
    print("  - optimization_results.json (detailed metrics)")
    print("  - optimization_bollinger.csv (exportable data)")
    print("\n💡 Review the heatmaps to identify optimal parameter combinations.")
    print("   Look for dark green areas (high profit) with good trade count.")
    print("="*80)


if __name__ == "__main__":
    main()
