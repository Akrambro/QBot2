import os
import time
import asyncio
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List, Dict, Tuple, Optional

from dotenv import load_dotenv
from pyquotex.stable_api import Quotex

from assets import live_assets, otc_assets
from utils import get_payout_filtered_assets
from strategies.engulfing_strategy import compute_engulfing_signal
from strategy_breakout import compute_signal as _compute_breakout_signal

def compute_breakout_signal_wrapper(candles: List[Dict]) -> Tuple[str, bool, str]:
    """Wrapper to match expected signature"""
    signal, valid = _compute_breakout_signal(candles)
    msg = f"Breakout {signal.upper()}" if valid else "No breakout"
    return signal, valid, msg


load_dotenv()


PAYOUT_THRESHOLD = float(os.getenv("QX_PAYOUT", "84"))
ASSET_LIST = live_assets + otc_assets
TRADE_PERCENT = float(os.getenv("QX_TRADE_PERCENT", "2")) / 100.0
ACCOUNT_MODE = os.getenv("QX_ACCOUNT", "PRACTICE").upper()
MAX_CONCURRENT = int(os.getenv("QX_MAX_CONCURRENT", "1"))
RUN_MINUTES = int(os.getenv("QX_RUN_MINUTES", "0"))
PAYOUT_REFRESH_MIN = int(os.getenv("QX_PAYOUT_REFRESH_MIN", "10"))
DAILY_PROFIT_LIMIT = float(os.getenv("QX_DAILY_PROFIT", "0"))
DAILY_PROFIT_IS_PERCENT = os.getenv("QX_DAILY_PROFIT_IS_PERCENT") == "1"
DAILY_LOSS_LIMIT = float(os.getenv("QX_DAILY_LOSS", "0"))
DAILY_LOSS_IS_PERCENT = os.getenv("QX_DAILY_LOSS_IS_PERCENT") == "1"

# Strategy configurations
BREAKOUT_ENABLED = os.getenv("QX_BREAKOUT_ENABLED", "1") == "1"
BREAKOUT_ANALYSIS_TF = int(os.getenv("QX_BREAKOUT_ANALYSIS_TF", "60"))
BREAKOUT_TRADE_TF = int(os.getenv("QX_BREAKOUT_TRADE_TF", "60"))
ENGULFING_ENABLED = os.getenv("QX_ENGULFING_ENABLED", "1") == "1"
ENGULFING_ANALYSIS_TF = int(os.getenv("QX_ENGULFING_ANALYSIS_TF", "60"))
ENGULFING_TRADE_TF = int(os.getenv("QX_ENGULFING_TRADE_TF", "60"))

# Global state with thread safety
import threading
state_lock = threading.Lock()
active_trade_count = 0
current_balance = 0
daily_pnl = 0
active_trades_by_asset = {}  # Track active trades per asset
failed_assets = set()  # Track assets with not_price errors


# Removed local compute_breakout_signal - using imported version


# Removed local compute_engulfing_signal - using imported version


async def fetch_candles_for_strategy(client: Quotex, asset: str, timeframe: int) -> Optional[List[Dict]]:
    try:
        api_asset = asset.replace('/', '').replace(' (OTC)', '_otc')
        # Fix timeframe units - timeframe is already in seconds
        candles = await client.get_candles(api_asset, time.time(), timeframe * 60, timeframe)
        return candles if candles and len(candles) >= 6 else None
    except Exception as e:
        print(f"⚠️ Candle fetch error for {asset}: {e}")
        return None


async def analyze_asset(client: Quotex, asset: str, trade_amount: float) -> Optional[Dict]:
    global active_trade_count, active_trades_by_asset
    
    # Check if we can place more trades
    if active_trade_count >= MAX_CONCURRENT:
        return None
    
    # Check if asset already has active trade
    if asset in active_trades_by_asset:
        return None
    
    results = []
    
    # Test breakout strategy if enabled
    if BREAKOUT_ENABLED:
        candles = await fetch_candles_for_strategy(client, asset, BREAKOUT_ANALYSIS_TF)
        if candles and len(candles) >= 6:
            try:
                signal, valid, msg = compute_breakout_signal_wrapper(candles)
                if valid:  # Only log when signal found to reduce noise
                    print(f"🔍 Breakout {asset}: {signal} | {valid} | {msg}")
                    results.append({
                        "asset": asset,
                        "signal": signal,
                        "strategy": "breakout",
                        "message": msg,
                        "amount": trade_amount,
                        "trade_timeframe": BREAKOUT_TRADE_TF
                    })
            except Exception as e:
                print(f"❌ Breakout strategy error for {asset}: {e}")
    
    # Test engulfing strategy if enabled
    if ENGULFING_ENABLED:
        candles = await fetch_candles_for_strategy(client, asset, ENGULFING_ANALYSIS_TF)
        if candles and len(candles) >= 6:
            try:
                signal, valid, msg = compute_engulfing_signal(candles)
                print(f"🔍 Engulfing {asset}: {signal} | {valid} | {msg}")
                if valid:
                    results.append({
                        "asset": asset,
                        "signal": signal,
                        "strategy": "engulfing",
                        "message": msg,
                        "amount": trade_amount,
                        "trade_timeframe": ENGULFING_TRADE_TF
                    })
            except Exception as e:
                print(f"❌ Engulfing strategy error for {asset}: {e}")
    
    # Return first valid signal (priority: breakout, then engulfing)
    return results[0] if results else None


async def place_trade_fast(client: Quotex, trade_data: Dict) -> bool:
    global active_trade_count, current_balance, active_trades_by_asset, failed_assets
    
    # Skip assets that recently failed with not_price
    if trade_data["asset"] in failed_assets:
        return False
    
    try:
        api_asset = trade_data["asset"].replace('/', '').replace(' (OTC)', '_otc')
        success, payload = await asyncio.wait_for(
            client.buy(
                amount=trade_data["amount"],
                asset=api_asset,
                direction=trade_data["signal"],
                duration=trade_data["trade_timeframe"],
                time_mode="TIME"
            ),
            timeout=5.0
        )
        
        if success and payload.get("id"):
            trade_id = payload["id"]
            
            # Thread-safe state updates
            with state_lock:
                active_trade_count += 1
                current_balance -= trade_data["amount"]
                active_trades_by_asset[trade_data["asset"]] = trade_id
            
            print(f"✅ {trade_data['strategy'].upper()} {trade_data['signal'].upper()} on {trade_data['asset']} - ID: {trade_id}")
            
            # Log trade
            log_entry = {
                "id": trade_id,
                "strategy": trade_data["strategy"],
                "timestamp": datetime.utcnow().isoformat(),
                "asset": trade_data["asset"],
                "direction": trade_data["signal"],
                "amount": trade_data["amount"],
                "duration": trade_data["trade_timeframe"],
                "status": "active",
                "pnl": 0,
                "account_mode": ACCOUNT_MODE
            }
            
            with open("trades.log", "a") as f:
                f.write(json.dumps(log_entry) + "\n")
            
            # Start monitoring trade result
            asyncio.create_task(monitor_trade_result(client, trade_id, log_entry, trade_data["asset"]))
            
            return True
        else:
            # Handle specific error codes
            error_msg = payload if isinstance(payload, str) else str(payload)
            if "not_price" in error_msg:
                print(f"⚠️ {trade_data['asset']} market closed - adding to skip list")
                failed_assets.add(trade_data["asset"])  # Skip this asset for future attempts
            elif "not_enough_money" in error_msg:
                print(f"⚠️ Insufficient balance for {trade_data['asset']}")
            else:
                print(f"❌ Trade failed on {trade_data['asset']}: {error_msg}")
            return False
    except asyncio.TimeoutError:
        print(f"⏰ Trade timeout on {trade_data['asset']} (>5s)")
        return False
    except Exception as e:
        print(f"❌ Trade error on {trade_data['asset']}: {e}")
        return False

async def monitor_trade_result(client: Quotex, trade_id: str, log_entry: Dict, asset: str):
    """Monitor trade result and update balance in real-time"""
    global active_trade_count, current_balance, daily_pnl, active_trades_by_asset
    
    def cleanup_trade():
        """Force cleanup this trade from counters"""
        global active_trade_count, active_trades_by_asset
        with state_lock:
            if active_trade_count > 0:
                active_trade_count -= 1
            if asset in active_trades_by_asset:
                del active_trades_by_asset[asset]
        print(f"🧹 Cleaned up trade {trade_id} for {asset} | Active: {active_trade_count}/{MAX_CONCURRENT}")
    
    try:
        # Wait for trade duration
        await asyncio.sleep(log_entry["duration"] + 5)
        
        # Check result
        won = await client.check_win(trade_id)
        profit = client.get_profit()
        
        # Thread-safe balance and PnL updates
        with state_lock:
            # Fix balance calculation - profit should be net result
            if won:
                current_balance += log_entry["amount"] + profit  # Get back amount + profit
            # For loss, we already deducted amount, so no change needed
            daily_pnl += profit
        
        # Update log entry
        log_entry["status"] = "win" if won else "loss"
        log_entry["pnl"] = profit
        # Get the current time for Asia/Kolkata
        now_ist = datetime.now(ZoneInfo("Asia/Kolkata"))  
        log_entry["timestamp"] = now_ist.isoformat()
        
        # Thread-safe file operations
        try:
            cleanup_old_trades()
            with open("trades.log", "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as file_error:
            print(f"⚠️ Log write error: {file_error}")
        
        result = "WON" if won else "LOST"
        print(f"🔔 Trade {trade_id} {result}: ${profit:.2f} | Daily P&L: ${daily_pnl:.2f}")
        
        # Always cleanup at the end
        cleanup_trade()
        
    except Exception as e:
        import traceback
        print(f"❌ Error monitoring trade {trade_id}: {e}")
        print(f"Stack trace: {traceback.format_exc()}")
        cleanup_trade()

def cleanup_old_trades():
    """Keep only last 30 trades in log file with thread safety"""
    try:
        log_file = "trades.log"
        if not os.path.exists(log_file):
            return
        
        # Use thread lock instead of file lock for cross-platform compatibility
        with state_lock:
            with open(log_file, "r") as f:
                lines = f.readlines()
            
            if len(lines) > 30:
                with open(log_file, "w") as f:
                    f.writelines(lines[-30:])
                
    except Exception as e:
        print(f"⚠️ Trade cleanup error: {e}")


async def wait_for_candle_close_and_analyze():
    """Wait until current candle closes for the shortest timeframe"""
    # Use the shortest enabled timeframe for synchronization
    timeframes = []
    if BREAKOUT_ENABLED:
        timeframes.append(BREAKOUT_ANALYSIS_TF)
    if ENGULFING_ENABLED:
        timeframes.append(ENGULFING_ANALYSIS_TF)
    
    if not timeframes:
        await asyncio.sleep(60)  # Default if no strategies enabled
        return
    
    min_timeframe = min(timeframes)
    now = int(time.time())
    remaining = min_timeframe - (now % min_timeframe)
    
    # Avoid waiting full period if already at boundary
    if remaining == min_timeframe:
        remaining = 0
    
    if remaining > 0:
        print(f"⏰ Waiting {remaining}s for candle close...")
        await asyncio.sleep(remaining + 0.1)
    else:
        print("📊 At candle boundary, analyzing immediately...")

async def get_actual_active_trades(client: Quotex) -> List[Dict]:
    """Get actual active trades from API to sync with our counter"""
    try:
        active_trades = await client.get_active_trades()
        return active_trades if active_trades else []
    except:
        return []

async def wait_next_candle_open(timeframe: int):
    now = int(time.time())
    remaining = timeframe - (now % timeframe)
    
    # Avoid waiting full period if already at boundary
    if remaining == timeframe:
        remaining = 0
        
    if remaining > 0:
        print(f"⏰ Waiting {remaining}s for next candle open...")
        await asyncio.sleep(remaining + 0.05)


async def main():
    global current_balance, daily_pnl, active_trade_count, active_trades_by_asset
    
    email = os.getenv("QX_EMAIL")
    password = os.getenv("QX_PASSWORD")

    client = Quotex(email=email, password=password, lang="en")
    client.set_account_mode("REAL" if ACCOUNT_MODE == "REAL" else "PRACTICE")
    connected, reason = await client.connect()
    if not connected:
        raise SystemExit(f"Failed to connect: {reason}")

    end_time = None if RUN_MINUTES == 0 else time.time() + RUN_MINUTES * 60
    last_payout_refresh = 0.0
    tradable_assets: List[str] = []
    daily_profit = 0
    
    balance = await client.get_balance()
    current_balance = balance
    initial_balance = balance
    trade_amount = round(max(balance * TRADE_PERCENT, 1.0), 2)
    
    enabled_strategies = []
    if BREAKOUT_ENABLED:
        enabled_strategies.append(f"Breakout({BREAKOUT_ANALYSIS_TF}s/{BREAKOUT_TRADE_TF}s)")
    if ENGULFING_ENABLED:
        enabled_strategies.append(f"Engulfing({ENGULFING_ANALYSIS_TF}s/{ENGULFING_TRADE_TF}s)")
    
    print(f"🚀 BOT STARTED | Mode: {ACCOUNT_MODE} | Balance: ${balance} | Trade: ${trade_amount}")
    print(f"📊 Strategies: {', '.join(enabled_strategies)} | Max Concurrent: {MAX_CONCURRENT}")

    # Thread-safe startup sync
    actual_active = await get_actual_active_trades(client)
    with state_lock:
        active_trade_count = len(actual_active)
        active_trades_by_asset.clear()
    print(f"🔄 Startup sync: Found {active_trade_count} actual active trades")
    
    # Start at next candle boundary (use shortest timeframe)
    timeframes = []
    if BREAKOUT_ENABLED:
        timeframes.append(BREAKOUT_ANALYSIS_TF)
    if ENGULFING_ENABLED:
        timeframes.append(ENGULFING_ANALYSIS_TF)
    
    min_timeframe = min(timeframes) if timeframes else 60
    await wait_next_candle_open(min_timeframe)

    while True:
        if end_time and time.time() >= end_time or os.path.exists("STOP"):
            break

        # Check daily limits using real-time values
        if DAILY_PROFIT_LIMIT > 0:
            limit = DAILY_PROFIT_LIMIT if not DAILY_PROFIT_IS_PERCENT else initial_balance * (DAILY_PROFIT_LIMIT / 100)
            if daily_pnl >= limit:
                print(f"🎉 PROFIT TARGET REACHED: ${daily_pnl:.2f} >= ${limit:.2f}")
                break

        if DAILY_LOSS_LIMIT > 0:
            limit = DAILY_LOSS_LIMIT if not DAILY_LOSS_IS_PERCENT else initial_balance * (DAILY_LOSS_LIMIT / 100)
            if daily_pnl <= -limit:
                print(f"🛑 LOSS LIMIT REACHED: ${daily_pnl:.2f} <= ${-limit:.2f}")
                break

        # Refresh assets and clear failed assets list periodically
        if time.time() - last_payout_refresh > PAYOUT_REFRESH_MIN * 60 or not tradable_assets:
            tradable_assets = await get_payout_filtered_assets(client, ASSET_LIST, PAYOUT_THRESHOLD)
            last_payout_refresh = time.time()
            # Clear failed assets list on refresh to retry them
            failed_assets.clear()
            print(f"🔄 Cleared failed assets list - will retry all assets")
        
        # Thread-safe active trades sync
        actual_active = await get_actual_active_trades(client)
        with state_lock:
            if len(actual_active) == 0 and (active_trade_count > 0 or active_trades_by_asset):
                print(f"🔄 RESETTING: No actual active trades found, clearing stuck counters")
                active_trade_count = 0
                active_trades_by_asset.clear()
            elif len(actual_active) != active_trade_count:
                print(f"🔄 SYNCING: Actual active trades ({len(actual_active)}) != counter ({active_trade_count})")
                active_trade_count = len(actual_active)
                active_trades_by_asset = {asset: trade_id for asset, trade_id in active_trades_by_asset.items() 
                                        if any(t.get('id') == trade_id for t in actual_active)}
            
        print(f"🎯 Assets: {len(tradable_assets)} | Active: {active_trade_count}/{MAX_CONCURRENT} | Balance: ${current_balance:.2f} | Daily P&L: ${daily_pnl:.2f}")

        # Wait for candle close, then analyze immediately
        await wait_for_candle_close_and_analyze()
        
        # Start 10-second timer for analysis and trade placement
        analysis_start = time.time()
        print(f"📊 Analyzing {len(tradable_assets)} assets at candle close...")
        
        # Filter out assets that recently failed with not_price
        active_assets = [asset for asset in tradable_assets if asset not in failed_assets]
        
        if len(active_assets) < len(tradable_assets):
            print(f"⚠️ Skipping {len(tradable_assets) - len(active_assets)} assets with recent failures")
        
        # Analyze active assets
        analysis_tasks = [analyze_asset(client, asset, trade_amount) for asset in active_assets]
        results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
        
        # Filter valid signals
        valid_trades = [r for r in results if isinstance(r, dict) and r is not None]
        
        analysis_time = time.time() - analysis_start
        print(f"🎯 Found {len(valid_trades)} signals in {analysis_time:.1f}s | Active: {active_trade_count}/{MAX_CONCURRENT}")
        
        # Check if we're within 15-second window
        if analysis_time > 15.0:
            print(f"⏰ TIMEOUT: Analysis took {analysis_time:.1f}s > 15s, skipping trades")
        elif valid_trades and active_trade_count < MAX_CONCURRENT:
            available_slots = MAX_CONCURRENT - active_trade_count
            trades_to_place = valid_trades[:available_slots]
            print(f"🚀 Placing {len(trades_to_place)} trades...")
            
            # Place trades with remaining time check
            trade_start = time.time()
            trade_tasks = [place_trade_fast(client, trade) for trade in trades_to_place]
            await asyncio.gather(*trade_tasks, return_exceptions=True)
            
            total_time = time.time() - analysis_start
            print(f"✅ Trade placement completed in {total_time:.1f}s total")
        elif valid_trades:
            print(f"⏸️ {len(valid_trades)} signals found but no capacity (Active: {active_trade_count}/{MAX_CONCURRENT})")
        else:
            print("❌ No signals found")
        
        # Continue to next cycle (already at candle boundary)

    print("🏁 Bot finished")


if __name__ == "__main__":
    asyncio.run(main())


