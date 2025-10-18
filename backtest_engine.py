"""
QBot2 Backtesting Engine

Comprehensive backtesting framework for strategy validation and optimization.
Tests strategies on historical data and provides detailed performance metrics.

Features:
- Individual strategy backtesting
- Parameter optimization
- Performance visualization
- Risk metrics calculation
- Trade-by-trade analysis

Author: QBot2 Trading System
Version: 1.0.0
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json
from pathlib import Path

# Import strategies
from strategies.breakout_strategy import check_extremes_condition, compute_breakout_signal
from strategies.engulfing_strategy import compute_engulfing_signal
from strategies.bollinger_break import compute_bollinger_break_signal


class BacktestEngine:
    """
    Backtesting engine for binary options strategies
    """
    
    def __init__(
        self,
        data_path: str,
        payout_rate: float = 0.85,
        trade_amount: float = 10.0,
        timeframe: int = 1  # Minutes per candle
    ):
        """
        Initialize backtesting engine
        
        Args:
            data_path: Path to CSV data file
            payout_rate: Payout rate (0.85 = 85% return on winning trades)
            trade_amount: Amount per trade
            timeframe: Candle timeframe in minutes
        """
        self.data_path = data_path
        self.payout_rate = payout_rate
        self.trade_amount = trade_amount
        self.timeframe = timeframe
        
        # Load and prepare data
        print(f"📊 Loading data from {data_path}...")
        self.df = self._load_data()
        print(f"✅ Loaded {len(self.df)} candles from {self.df.index[0]} to {self.df.index[-1]}")
        
        # Results storage
        self.results = {}
    
    def _load_data(self) -> pd.DataFrame:
        """Load and prepare CSV data"""
        df = pd.read_csv(
            self.data_path,
            sep='\t',
            header=None,
            names=['timestamp', 'open', 'high', 'low', 'close', 'volume'],
            parse_dates=['timestamp'],
            index_col='timestamp'
        )
        
        # Add derived columns for strategies
        df['max'] = df['high']
        df['min'] = df['low']
        
        return df
    
    def prepare_candles(self, start_idx: int, lookback: int = 30) -> List[Dict]:
        """
        Prepare candle data in the format strategies expect
        
        Args:
            start_idx: Current candle index
            lookback: Number of historical candles to include
            
        Returns:
            List of candle dictionaries
        """
        # Get lookback candles + current candle
        start = max(0, start_idx - lookback + 1)
        end = start_idx + 1
        
        candles = []
        for i in range(start, end):
            row = self.df.iloc[i]
            candles.append({
                'timestamp': row.name,
                'open': row['open'],
                'close': row['close'],
                'high': row['high'],
                'low': row['low'],
                'max': row['max'],
                'min': row['min'],
                'volume': row['volume']
            })
        
        return candles
    
    def simulate_trade(
        self,
        entry_idx: int,
        signal: str,
        duration_minutes: int = 1
    ) -> Tuple[bool, float]:
        """
        Simulate a binary options trade
        
        Args:
            entry_idx: Index where trade is entered
            signal: 'call' or 'put'
            duration_minutes: Trade duration in minutes
            
        Returns:
            (won, profit/loss)
        """
        # Check if we have enough data for the trade duration
        if entry_idx + duration_minutes >= len(self.df):
            return False, 0.0
        
        entry_price = self.df.iloc[entry_idx]['close']
        exit_idx = entry_idx + duration_minutes
        exit_price = self.df.iloc[exit_idx]['close']
        
        # Determine win/loss
        if signal.lower() == 'call':
            won = exit_price > entry_price
        elif signal.lower() == 'put':
            won = exit_price < entry_price
        else:
            return False, 0.0
        
        # Calculate profit/loss
        if won:
            profit = self.trade_amount * self.payout_rate
        else:
            profit = -self.trade_amount
        
        return won, profit
    
    def backtest_breakout(
        self,
        lookback: int = 30,
        start_candle: int = 100,
        end_candle: Optional[int] = None
    ) -> Dict:
        """
        Backtest breakout strategy
        
        Args:
            lookback: Number of candles to use for analysis
            start_candle: Start index for backtesting
            end_candle: End index (None = use all data)
            
        Returns:
            Dictionary with backtest results
        """
        print("\n" + "="*80)
        print("🔍 BACKTESTING: BREAKOUT STRATEGY")
        print("="*80)
        
        if end_candle is None or end_candle > len(self.df) - 2:
            end_candle = len(self.df) - 2
        
        if start_candle < 0:
            start_candle = 0
        
        trades = []
        equity_curve = [0]
        current_equity = 0
        
        for i in range(start_candle, end_candle):
            if i >= len(self.df) - 2:  # Safety check
                break
            
            candles = self.prepare_candles(i, lookback)
            
            if len(candles) < 10:
                continue
            
            # Check for breakout signal
            is_low_extreme, is_high_extreme = check_extremes_condition(candles)
            
            if is_low_extreme or is_high_extreme:
                extremes = (is_low_extreme, is_high_extreme)
                signal, valid, msg = compute_breakout_signal(candles, extremes)
                
                if valid:
                    # Simulate trade on NEXT candle
                    won, pnl = self.simulate_trade(i + 1, signal, duration_minutes=1)
                    
                    current_equity += pnl
                    equity_curve.append(current_equity)
                    
                    trades.append({
                        'entry_time': self.df.index[i + 1],
                        'signal': signal,
                        'entry_price': self.df.iloc[i + 1]['close'],
                        'exit_price': self.df.iloc[i + 2]['close'],
                        'won': won,
                        'pnl': pnl,
                        'equity': current_equity,
                        'reason': msg
                    })
        
        # Calculate metrics
        results = self._calculate_metrics(trades, equity_curve, "Breakout Strategy")
        self.results['breakout'] = results
        
        return results
    
    def backtest_engulfing(
        self,
        lookback: int = 30,
        start_candle: int = 100,
        end_candle: Optional[int] = None
    ) -> Dict:
        """
        Backtest engulfing strategy
        
        Args:
            lookback: Number of candles to use for analysis
            start_candle: Start index for backtesting
            end_candle: End index (None = use all data)
            
        Returns:
            Dictionary with backtest results
        """
        print("\n" + "="*80)
        print("🔍 BACKTESTING: ENGULFING STRATEGY")
        print("="*80)
        
        if end_candle is None or end_candle > len(self.df) - 2:
            end_candle = len(self.df) - 2
        
        if start_candle < 0:
            start_candle = 0
        
        trades = []
        equity_curve = [0]
        current_equity = 0
        
        for i in range(start_candle, end_candle):
            if i >= len(self.df) - 2:  # Safety check
                break
            
            candles = self.prepare_candles(i, lookback)
            
            if len(candles) < 10:
                continue
            
            # Check for engulfing signal
            signal, valid, msg = compute_engulfing_signal(candles)
            
            if valid:
                # Simulate trade on NEXT candle
                won, pnl = self.simulate_trade(i + 1, signal, duration_minutes=1)
                
                current_equity += pnl
                equity_curve.append(current_equity)
                
                trades.append({
                    'entry_time': self.df.index[i + 1],
                    'signal': signal,
                    'entry_price': self.df.iloc[i + 1]['close'],
                    'exit_price': self.df.iloc[i + 2]['close'],
                    'won': won,
                    'pnl': pnl,
                    'equity': current_equity,
                    'reason': msg
                })
        
        results = self._calculate_metrics(trades, equity_curve, "Engulfing Strategy")
        self.results['engulfing'] = results
        
        return results
    
    def backtest_bollinger(
        self,
        period: int = 14,
        deviation: float = 1.0,
        lookback: int = 30,
        start_candle: int = 100,
        end_candle: Optional[int] = None
    ) -> Dict:
        """
        Backtest Bollinger Band breakout strategy
        
        Args:
            period: Bollinger Band period
            deviation: Standard deviation multiplier
            lookback: Number of candles to use for analysis
            start_candle: Start index for backtesting
            end_candle: End index (None = use all data)
            
        Returns:
            Dictionary with backtest results
        """
        print("\n" + "="*80)
        print(f"🔍 BACKTESTING: BOLLINGER BREAK STRATEGY (Period={period}, Dev={deviation})")
        print("="*80)
        
        if end_candle is None or end_candle > len(self.df) - 2:
            end_candle = len(self.df) - 2
        
        # Ensure start_candle is valid
        if start_candle < 0:
            start_candle = 0
        
        trades = []
        equity_curve = [0]
        current_equity = 0
        
        for i in range(start_candle, end_candle):
            if i >= len(self.df) - 2:  # Safety check
                break
            
            candles = self.prepare_candles(i, lookback)
            
            if len(candles) < period + 1:
                continue
            
            # Check for Bollinger signal
            signal, valid, msg = compute_bollinger_break_signal(candles, period, deviation)
            
            if valid:
                # Simulate trade on NEXT candle
                won, pnl = self.simulate_trade(i + 1, signal, duration_minutes=1)
                
                current_equity += pnl
                equity_curve.append(current_equity)
                
                trades.append({
                    'entry_time': self.df.index[i + 1],
                    'signal': signal,
                    'entry_price': self.df.iloc[i + 1]['close'],
                    'exit_price': self.df.iloc[i + 2]['close'],
                    'won': won,
                    'pnl': pnl,
                    'equity': current_equity,
                    'reason': msg
                })
        
        results = self._calculate_metrics(
            trades, 
            equity_curve, 
            f"Bollinger Break (P={period}, D={deviation})"
        )
        self.results[f'bollinger_{period}_{deviation}'] = results
        
        return results
    
    def _calculate_metrics(
        self,
        trades: List[Dict],
        equity_curve: List[float],
        strategy_name: str
    ) -> Dict:
        """Calculate comprehensive performance metrics"""
        
        if not trades:
            print(f"⚠️ No trades executed for {strategy_name}")
            return {
                'strategy': strategy_name,
                'total_trades': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0.0,
                'total_profit': 0.0,
                'trades': [],
                'equity_curve': equity_curve
            }
        
        wins = [t for t in trades if t['won']]
        losses = [t for t in trades if not t['won']]
        
        win_rate = (len(wins) / len(trades)) * 100 if trades else 0
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
        
        # Expected value per trade
        expected_value = total_profit / len(trades) if trades else 0
        
        results = {
            'strategy': strategy_name,
            'total_trades': len(trades),
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
            'trades': trades,
            'equity_curve': equity_curve
        }
        
        # Print summary
        print(f"\n📊 {strategy_name} Results:")
        print(f"   Total Trades: {len(trades)}")
        print(f"   Wins: {len(wins)} | Losses: {len(losses)}")
        print(f"   Win Rate: {win_rate:.2f}%")
        print(f"   Total Profit: ${total_profit:.2f}")
        print(f"   Avg Win: ${avg_win:.2f} | Avg Loss: ${avg_loss:.2f}")
        print(f"   Profit Factor: {profit_factor:.2f}")
        print(f"   Max Drawdown: ${max_dd:.2f} ({max_dd_pct:.2f}%)")
        print(f"   Expected Value/Trade: ${expected_value:.2f}")
        
        return results
    
    def optimize_bollinger(
        self,
        period_range: Tuple[int, int] = (10, 20),
        deviation_range: Tuple[float, float] = (0.5, 2.0),
        step_period: int = 2,
        step_deviation: float = 0.5
    ) -> pd.DataFrame:
        """
        Optimize Bollinger Band parameters
        
        Args:
            period_range: (min, max) period to test
            deviation_range: (min, max) deviation to test
            step_period: Step size for period
            step_deviation: Step size for deviation
            
        Returns:
            DataFrame with optimization results
        """
        print("\n" + "="*80)
        print("🔧 OPTIMIZING BOLLINGER PARAMETERS")
        print("="*80)
        
        results_list = []
        
        periods = range(period_range[0], period_range[1] + 1, step_period)
        deviations = np.arange(deviation_range[0], deviation_range[1] + step_deviation, step_deviation)
        
        total_tests = len(periods) * len(deviations)
        test_num = 0
        
        for period in periods:
            for deviation in deviations:
                test_num += 1
                print(f"\n[{test_num}/{total_tests}] Testing Period={period}, Deviation={deviation:.1f}")
                
                results = self.backtest_bollinger(period=period, deviation=deviation)
                
                results_list.append({
                    'period': period,
                    'deviation': deviation,
                    'total_trades': results['total_trades'],
                    'win_rate': results['win_rate'],
                    'total_profit': results['total_profit'],
                    'profit_factor': results['profit_factor'],
                    'max_drawdown': results['max_drawdown'],
                    'expected_value': results['expected_value']
                })
        
        df_results = pd.DataFrame(results_list)
        
        # Find best parameters
        if len(df_results) > 0:
            best_idx = df_results['total_profit'].idxmax()
            best = df_results.loc[best_idx]
            
            print("\n" + "="*80)
            print("🏆 BEST PARAMETERS:")
            print(f"   Period: {int(best['period'])}")
            print(f"   Deviation: {best['deviation']:.1f}")
            print(f"   Win Rate: {best['win_rate']:.2f}%")
            print(f"   Total Profit: ${best['total_profit']:.2f}")
            print(f"   Profit Factor: {best['profit_factor']:.2f}")
            print("="*80)
        
        return df_results
    
    def plot_results(self, strategy_names: Optional[List[str]] = None):
        """
        Create comprehensive visualization of backtest results
        
        Args:
            strategy_names: List of strategies to plot (None = all)
        """
        if not self.results:
            print("⚠️ No backtest results to plot. Run backtests first.")
            return
        
        if strategy_names is None:
            strategy_names = list(self.results.keys())
        
        # Filter results
        plot_results = {k: v for k, v in self.results.items() if k in strategy_names}
        
        if not plot_results:
            print(f"⚠️ No results found for strategies: {strategy_names}")
            return
        
        # Create subplots
        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=(
                'Equity Curves',
                'Win Rate Comparison',
                'Profit/Loss Distribution',
                'Trade Distribution',
                'Cumulative Performance',
                'Risk Metrics'
            ),
            specs=[
                [{"secondary_y": False}, {"type": "bar"}],
                [{"type": "bar"}, {"type": "bar"}],
                [{"secondary_y": False}, {"type": "bar"}]
            ]
        )
        
        colors = ['#00D9FF', '#FF6B9D', '#C779D0', '#4ECDC4', '#FFE66D']
        
        # Plot 1: Equity Curves
        for idx, (name, results) in enumerate(plot_results.items()):
            fig.add_trace(
                go.Scatter(
                    x=list(range(len(results['equity_curve']))),
                    y=results['equity_curve'],
                    name=results['strategy'],
                    line=dict(color=colors[idx % len(colors)], width=2)
                ),
                row=1, col=1
            )
        
        # Plot 2: Win Rate Comparison
        strategies = [r['strategy'] for r in plot_results.values()]
        win_rates = [r['win_rate'] for r in plot_results.values()]
        
        fig.add_trace(
            go.Bar(
                x=strategies,
                y=win_rates,
                name='Win Rate',
                marker_color=colors[:len(strategies)]
            ),
            row=1, col=2
        )
        
        # Plot 3: Profit/Loss Distribution
        for idx, (name, results) in enumerate(plot_results.items()):
            wins_pnl = [t['pnl'] for t in results['trades'] if t['won']]
            losses_pnl = [t['pnl'] for t in results['trades'] if not t['won']]
            
            fig.add_trace(
                go.Bar(
                    x=[results['strategy']],
                    y=[sum(wins_pnl) if wins_pnl else 0],
                    name=f"{results['strategy']} Wins",
                    marker_color='green',
                    showlegend=False
                ),
                row=2, col=1
            )
            
            fig.add_trace(
                go.Bar(
                    x=[results['strategy']],
                    y=[abs(sum(losses_pnl)) if losses_pnl else 0],
                    name=f"{results['strategy']} Losses",
                    marker_color='red',
                    showlegend=False
                ),
                row=2, col=1
            )
        
        # Plot 4: Trade Distribution
        total_trades = [r['total_trades'] for r in plot_results.values()]
        
        fig.add_trace(
            go.Bar(
                x=strategies,
                y=total_trades,
                name='Total Trades',
                marker_color=colors[:len(strategies)]
            ),
            row=2, col=2
        )
        
        # Plot 5: Cumulative Performance
        for idx, (name, results) in enumerate(plot_results.items()):
            trades_df = pd.DataFrame(results['trades'])
            if len(trades_df) > 0:
                trades_df['cumulative_pnl'] = trades_df['pnl'].cumsum()
                
                fig.add_trace(
                    go.Scatter(
                        x=trades_df['entry_time'],
                        y=trades_df['cumulative_pnl'],
                        name=results['strategy'],
                        line=dict(color=colors[idx % len(colors)], width=2)
                    ),
                    row=3, col=1
                )
        
        # Plot 6: Risk Metrics
        max_drawdowns = [r['max_drawdown'] for r in plot_results.values()]
        
        fig.add_trace(
            go.Bar(
                x=strategies,
                y=max_drawdowns,
                name='Max Drawdown',
                marker_color='orange'
            ),
            row=3, col=2
        )
        
        # Update layout
        fig.update_layout(
            title_text="QBot2 Backtesting Results - Strategy Comparison",
            showlegend=True,
            height=1200,
            template='plotly_dark'
        )
        
        fig.update_xaxes(title_text="Trade Number", row=1, col=1)
        fig.update_yaxes(title_text="Equity ($)", row=1, col=1)
        
        fig.update_xaxes(title_text="Strategy", row=1, col=2)
        fig.update_yaxes(title_text="Win Rate (%)", row=1, col=2)
        
        fig.update_xaxes(title_text="Strategy", row=2, col=1)
        fig.update_yaxes(title_text="P/L ($)", row=2, col=1)
        
        fig.update_xaxes(title_text="Strategy", row=2, col=2)
        fig.update_yaxes(title_text="Trade Count", row=2, col=2)
        
        fig.update_xaxes(title_text="Time", row=3, col=1)
        fig.update_yaxes(title_text="Cumulative P/L ($)", row=3, col=1)
        
        fig.update_xaxes(title_text="Strategy", row=3, col=2)
        fig.update_yaxes(title_text="Max Drawdown ($)", row=3, col=2)
        
        # Save plot
        output_file = "backtest_results.html"
        fig.write_html(output_file)
        print(f"\n✅ Results saved to: {output_file}")
        
        # Show plot
        fig.show()
    
    def save_results(self, filename: str = "backtest_results.json"):
        """Save backtest results to JSON file"""
        # Convert results for JSON serialization
        serializable_results = {}
        
        for key, result in self.results.items():
            serializable_results[key] = {
                'strategy': result['strategy'],
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
        
        with open(filename, 'w') as f:
            json.dump(serializable_results, f, indent=2)
        
        print(f"\n✅ Results saved to: {filename}")


if __name__ == "__main__":
    print("="*80)
    print("🚀 QBot2 Backtesting Engine")
    print("="*80)
    
    # Initialize engine
    engine = BacktestEngine(
        data_path="data/usdjpy_100k.csv",
        payout_rate=0.85,  # 85% payout
        trade_amount=10.0
    )
    
    # Run backtests
    print("\n🔬 Running strategy backtests...")
    
    breakout_results = engine.backtest_breakout()
    engulfing_results = engine.backtest_engulfing()
    bollinger_results = engine.backtest_bollinger(period=14, deviation=1.0)
    
    # Plot results
    print("\n📊 Generating visualizations...")
    engine.plot_results()
    
    # Save results
    engine.save_results()
    
    print("\n✅ Backtesting complete!")
