import os
import time
import asyncio
import json
import signal
from datetime import datetime
from typing import List, Dict, Optional

from dotenv import load_dotenv
from pyquotex.stable_api import Quotex

from assets import live_assets, otc_assets
from utils import get_payout_filtered_assets
from strategies.breakout_strategy import check_extremes_condition, compute_breakout_signal
from strategies.engulfing_strategy import compute_engulfing_signal

load_dotenv()

# Configuration
PAYOUT_THRESHOLD = float(os.getenv("QX_PAYOUT", "84"))
TRADE_PERCENT = float(os.getenv("QX_TRADE_PERCENT", "2")) / 100.0
ACCOUNT_MODE = os.getenv("QX_ACCOUNT", "PRACTICE").upper()
MAX_CONCURRENT = int(os.getenv("QX_MAX_CONCURRENT", "1"))
TIMEFRAME = int(os.getenv("QX_TIMEFRAME", "60"))
BREAKOUT_ENABLED = os.getenv("QX_BREAKOUT_ENABLED", "1") == "1"
ENGULFING_ENABLED = os.getenv("QX_ENGULFING_ENABLED", "1") == "1"

# Global state
active_trades = {}
failed_assets = set()
shutdown_requested = False

def signal_handler(signum, frame):
    global shutdown_requested
    print(f"\n🛑 Shutdown requested")
    shutdown_requested = True

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

async def fetch_candles(client: Quotex, asset: str) -> Optional[List[Dict]]:
    try:
        api_asset = asset.replace('/', '').replace(' (OTC)', '_otc')
        candles = await client.get_candles(api_asset, time.time(), TIMEFRAME * 60, TIMEFRAME)
        return candles if candles and len(candles) >= 6 else None
    except Exception as e:
        print(f"⚠️ {asset}: Candle fetch error - {e}")
        return None

async def check_breakout_signals(client: Quotex, assets: List[str]) -> List[Dict]:
    signals = []
    if not BREAKOUT_ENABLED:
        return signals
    
    print(f"🔍 Checking breakout on {len(assets)} assets...")
    
    for asset in assets:
        if asset in active_trades or asset in failed_assets:
            continue
            
        candles = await fetch_candles(client, asset)
        if not candles:
            continue
            
        # Check if previous candle is extreme
        is_low_extreme, is_high_extreme = check_extremes_condition(candles)
        
        if is_low_extreme or is_high_extreme:
            print(f"📊 {asset}: Extreme found - Low={is_low_extreme}, High={is_high_extreme}")
            
            # Check for breakout signal
            signal, valid, msg = compute_breakout_signal(candles, (is_low_extreme, is_high_extreme))
            if valid:
                signals.append({
                    "asset": asset,
                    "signal": signal,
                    "strategy": "breakout"
                })
                print(f"🎯 BREAKOUT {signal.upper()}: {asset}")
    
    return signals

async def check_engulfing_signals(client: Quotex, assets: List[str]) -> List[Dict]:
    signals = []
    if not ENGULFING_ENABLED:
        return signals
    
    print(f"🔍 Checking engulfing on {len(assets)} assets...")
    
    for asset in assets:
        if asset in active_trades or asset in failed_assets:
            continue
            
        candles = await fetch_candles(client, asset)
        if not candles:
            continue
            
        signal, valid, msg = compute_engulfing_signal(candles)
        if valid:
            signals.append({
                "asset": asset,
                "signal": signal,
                "strategy": "engulfing"
            })
            print(f"🎯 ENGULFING {signal.upper()}: {asset}")
    
    return signals

async def place_trade(client: Quotex, signal_data: Dict, trade_amount: float) -> bool:
    global active_trades, failed_assets
    
    asset = signal_data["asset"]
    signal = signal_data["signal"]
    strategy = signal_data["strategy"]
    
    try:
        api_asset = asset.replace('/', '').replace(' (OTC)', '_otc')
        success, payload = await asyncio.wait_for(
            client.buy(
                amount=trade_amount,
                asset=api_asset,
                direction=signal,
                duration=TIMEFRAME,
                time_mode="TIME"
            ),
            timeout=3.0
        )
        
        if success and payload.get("id"):
            trade_id = payload["id"]
            active_trades[asset] = trade_id
            
            print(f"✅ {strategy.upper()} {signal.upper()} on {asset} - ID: {trade_id}")
            
            # Log trade
            log_entry = {
                "id": trade_id,
                "strategy": strategy,
                "timestamp": datetime.utcnow().isoformat(),
                "asset": asset,
                "direction": signal,
                "amount": trade_amount,
                "duration": TIMEFRAME,
                "status": "active",
                "pnl": 0
            }
            
            with open("trades.log", "a") as f:
                f.write(json.dumps(log_entry) + "\n")
            
            # Monitor result
            asyncio.create_task(monitor_trade(client, trade_id, log_entry, asset))
            return True
        else:
            error_msg = str(payload)
            if "not_price" in error_msg:
                failed_assets.add(asset)
                print(f"⚠️ {asset}: Market closed")
            else:
                print(f"❌ {asset}: Trade failed - {error_msg}")
            return False
            
    except asyncio.TimeoutError:
        print(f"⏰ {asset}: Trade timeout")
        return False
    except Exception as e:
        print(f"❌ {asset}: Trade error - {e}")
        return False

async def monitor_trade(client: Quotex, trade_id: str, log_entry: Dict, asset: str):
    global active_trades
    
    try:
        # Wait for trade duration + buffer
        await asyncio.sleep(TIMEFRAME + 5)
        
        # Check result
        won = await client.check_win(trade_id)
        profit = client.get_profit()
        
        # Update log
        log_entry["status"] = "win" if won else "loss"
        log_entry["pnl"] = profit
        log_entry["timestamp"] = datetime.utcnow().isoformat()
        
        with open("trades.log", "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        
        result = "WON" if won else "LOST"
        print(f"🔔 Trade {trade_id} {result}: ${profit:.2f}")
        
        # Cleanup
        if asset in active_trades:
            del active_trades[asset]
            
    except Exception as e:
        print(f"❌ Monitor error for {trade_id}: {e}")
        if asset in active_trades:
            del active_trades[asset]

async def wait_for_candle_close():
    now = int(time.time())
    remaining = TIMEFRAME - (now % TIMEFRAME)
    
    if remaining == TIMEFRAME:
        remaining = 0
    
    if remaining > 0:
        print(f"⏰ Waiting {remaining}s for candle close...")
        for _ in range(remaining):
            if shutdown_requested or os.path.exists("STOP"):
                return
            await asyncio.sleep(1)

async def main():
    global active_trades, failed_assets
    
    # Connect
    email = os.getenv("QX_EMAIL")
    password = os.getenv("QX_PASSWORD")
    
    client = Quotex(email=email, password=password, lang="en")
    client.set_account_mode("REAL" if ACCOUNT_MODE == "REAL" else "PRACTICE")
    
    connected, reason = await client.connect()
    if not connected:
        raise SystemExit(f"Failed to connect: {reason}")
    
    # Get balance and calculate trade amount
    balance = await client.get_balance()
    trade_amount = round(max(balance * TRADE_PERCENT, 1.0), 2)
    
    print(f"🚀 BOT STARTED | Mode: {ACCOUNT_MODE} | Balance: ${balance} | Trade: ${trade_amount}")
    print(f"📊 Timeframe: {TIMEFRAME}s | Breakout: {BREAKOUT_ENABLED} | Engulfing: {ENGULFING_ENABLED}")
    
    # Get tradable assets
    all_assets = live_assets + otc_assets
    tradable_assets = await get_payout_filtered_assets(client, all_assets, PAYOUT_THRESHOLD)
    print(f"🎯 Tradable assets: {len(tradable_assets)}")
    
    # Wait for next candle boundary
    await wait_for_candle_close()
    
    while True:
        # Check shutdown
        if shutdown_requested or os.path.exists("STOP"):
            break
        
        # Clear failed assets periodically
        if len(failed_assets) > 0 and int(time.time()) % 300 == 0:  # Every 5 minutes
            failed_assets.clear()
            print("🔄 Cleared failed assets")
        
        print(f"\n📊 ANALYZING | Active trades: {len(active_trades)}/{MAX_CONCURRENT}")
        
        # Filter available assets
        available_assets = [asset for asset in tradable_assets 
                          if asset not in active_trades and asset not in failed_assets]
        
        if len(active_trades) >= MAX_CONCURRENT:
            print("⏸️ Max concurrent trades reached")
        elif not available_assets:
            print("❌ No available assets")
        else:
            # Get signals from all strategies
            start_time = time.time()
            
            breakout_signals = await check_breakout_signals(client, available_assets)
            engulfing_signals = await check_engulfing_signals(client, available_assets)
            
            all_signals = breakout_signals + engulfing_signals
            analysis_time = time.time() - start_time
            
            print(f"🎯 Found {len(all_signals)} signals in {analysis_time:.1f}s")
            
            # Place trades (respect max concurrent limit)
            if all_signals and analysis_time < 10.0:  # Within 10s window
                available_slots = MAX_CONCURRENT - len(active_trades)
                signals_to_trade = all_signals[:available_slots]
                
                print(f"🚀 Placing {len(signals_to_trade)} trades...")
                
                trade_tasks = [place_trade(client, signal, trade_amount) for signal in signals_to_trade]
                await asyncio.gather(*trade_tasks, return_exceptions=True)
            elif analysis_time >= 10.0:
                print(f"⏰ Analysis too slow ({analysis_time:.1f}s), skipping trades")
        
        # Wait for next candle
        await wait_for_candle_close()
    
    print("🏁 Bot finished")
    
    # Cleanup
    if os.path.exists("STOP"):
        os.remove("STOP")

if __name__ == "__main__":
    asyncio.run(main())