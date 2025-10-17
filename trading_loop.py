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
trade_semaphore = None  # Will be initialized in main()
shortlisted_assets = {}  # Breakout prefiltered assets
engulfing_candles_cache = {}  # Early fetched candles for engulfing
last_shortlist_time = 0
last_connection_check = 0

def signal_handler(signum, frame):
    global shutdown_requested
    print(f"\n🛑 Shutdown requested")
    shutdown_requested = True

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

async def fetch_candles(client: Quotex, asset: str) -> Optional[List[Dict]]:
    try:
        api_asset = asset.replace('/', '').replace(' (OTC)', '_otc')
        
        # Use proper pyquotex parameters: asset, end_from_time, count, period
        end_time = int(time.time())
        count = 10  # Get more candles for better analysis
        period = TIMEFRAME  # Period in seconds
        
        candles = await client.get_candles(api_asset, end_time, count, period)
        
        # Validate candle data - check if values make sense for the asset
        if candles and len(candles) >= 6:
            last_candle = candles[-1]
            prev_candle = candles[-2]
            
            # Basic validation - check if candle values are reasonable
            curr_price = float(last_candle['close'])
            prev_price = float(prev_candle['close'])
            
            # Asset-specific price validation
            if 'JPY' in asset and (curr_price < 50 or curr_price > 200):
                print(f"⚠️ {asset}: Invalid JPY price {curr_price} - data corruption detected")
                return None
            elif 'NGN' in asset and (curr_price < 1000 or curr_price > 2000):
                print(f"⚠️ {asset}: Invalid NGN price {curr_price} - data corruption detected")
                return None
            elif 'BDT' in asset and (curr_price < 100 or curr_price > 150):
                print(f"⚠️ {asset}: Invalid BDT price {curr_price} - data corruption detected")
                return None
            elif 'TRY' in asset and (curr_price < 30 or curr_price > 50):
                # This is expected range for USD/TRY
                pass
            elif curr_price < 0.1 or curr_price > 10000:
                print(f"⚠️ {asset}: Invalid price range {curr_price} - data corruption detected")
                return None
            

        
        return candles if candles and len(candles) >= 6 else None
    except Exception as e:
        print(f"⚠️ {asset}: Candle fetch error - {e}")
        return None

async def prefilter_breakout_assets(client: Quotex, assets: List[str]) -> None:
    """Phase 1: Prefilter assets for breakout strategy at half-time"""
    global shortlisted_assets, last_shortlist_time
    
    current_time = int(time.time())
    if current_time - last_shortlist_time < 10:  # Avoid too frequent updates
        return
    
    print(f"🔍 Prefiltering {len(assets)} assets for breakout extremes...")
    shortlisted_assets.clear()
    
    # Sequential fetching to prevent data corruption
    for asset in assets:
        if asset in active_trades or asset in failed_assets:
            continue
            
        candles = await fetch_candles(client, asset)
        if candles and len(candles) >= 6:
            is_low_extreme, is_high_extreme = check_extremes_condition(candles)
            if is_low_extreme or is_high_extreme:
                shortlisted_assets[asset] = (is_low_extreme, is_high_extreme)
        
        await asyncio.sleep(0.2)  # Delay between requests
    
    last_shortlist_time = current_time
    print(f"✅ Shortlisted {len(shortlisted_assets)} assets: {list(shortlisted_assets.keys())}")

async def prefetch_engulfing_candles(client: Quotex, assets: List[str]) -> None:
    """Phase 0: Prefetch candles for engulfing strategy at candle start"""
    global engulfing_candles_cache
    
    if not ENGULFING_ENABLED:
        return
    
    print(f"🔍 Prefetching candles for {len(assets)} assets...")
    engulfing_candles_cache.clear()
    
    # Sequential fetching to prevent data corruption
    for asset in assets:
        if asset not in active_trades and asset not in failed_assets:
            await fetch_and_cache_candles(client, asset)
            await asyncio.sleep(0.2)  # Delay between requests
    
    print(f"✅ Cached candles for {len(engulfing_candles_cache)} assets")

async def fetch_and_cache_candles(client: Quotex, asset: str) -> None:
    """Fetch and cache candles for an asset"""
    candles = await fetch_candles(client, asset)
    if candles:
        engulfing_candles_cache[asset] = candles

async def analyze_asset(client: Quotex, asset: str, trade_amount: float) -> Optional[Dict]:
    """Analyze single asset for all strategies and return signal if found"""
    if asset in active_trades or asset in failed_assets:
        return None
    

    
    # Check breakout strategy (use shortlisted assets only)
    if BREAKOUT_ENABLED and asset in shortlisted_assets:

        # Use fresh candles for final analysis to get latest data
        candles = await fetch_candles(client, asset)
        if candles and len(candles) >= 6:
            extremes = shortlisted_assets[asset]
            signal, valid, msg = compute_breakout_signal(candles, extremes)

            if valid:
                print(f"✅ {asset} BREAKOUT SIGNAL GENERATED: {signal.upper()}")
                return {
                    "asset": asset,
                    "signal": signal,
                    "strategy": "breakout"
                }



    
    # Check engulfing strategy (use cached candles)
    if ENGULFING_ENABLED and asset in engulfing_candles_cache:

        candles = engulfing_candles_cache[asset]
        signal, valid, msg = compute_engulfing_signal(candles)

        if valid:
            print(f"✅ {asset} ENGULFING SIGNAL GENERATED: {signal.upper()}")
            return {
                "asset": asset,
                "signal": signal,
                "strategy": "engulfing"
            }

    return None

async def analyze_and_trade(client: Quotex, asset: str, trade_amount: float) -> bool:
    """Analyze asset and immediately place trade if signal found"""
    try:
        signal_data = await analyze_asset(client, asset, trade_amount)
        
        if signal_data:
            print(f"🎯 {signal_data['strategy'].upper()} {signal_data['signal'].upper()}: {asset}")
            return await place_trade(client, signal_data, trade_amount)
        
        return False
    except Exception as e:
        print(f"⚠️ {asset}: Analysis error - {e}")
        return False

async def place_trade(client: Quotex, signal_data: Dict, trade_amount: float) -> bool:
    global active_trades, failed_assets, trade_semaphore
    
    asset = signal_data["asset"]
    signal = signal_data["signal"]
    strategy = signal_data["strategy"]
    
    # Use semaphore to limit concurrent trades
    async with trade_semaphore:
        if asset in active_trades:  # Double-check after acquiring semaphore
            return False
            
        try:
            api_asset = asset.replace('/', '').replace(' (OTC)', '_otc')
            success, payload = await asyncio.wait_for(
                client.buy(
                    amount=trade_amount,
                    asset=api_asset,
                    direction=signal,
                    duration=TIMEFRAME
                ),
                timeout=5.0
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
                    f.flush()  # Force write to disk immediately
                
                # Monitor result
                asyncio.create_task(monitor_trade(client, trade_id, log_entry, asset))
                return True
            else:
                print(f"❌ {asset}: Trade failed - {payload}")
                if isinstance(payload, str) and "market" in payload.lower():
                    failed_assets.add(asset)
                
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
        
        # Check result with timeout protection
        try:
            won = await asyncio.wait_for(client.check_win(trade_id), timeout=10.0)
            profit = await asyncio.wait_for(client.get_profit(), timeout=5.0)
        except asyncio.TimeoutError:
            print(f"⏰ {asset}: Monitor timeout - forcing cleanup")
            won = False
            profit = 0
        
        # Update log
        log_entry["status"] = "win" if won else "loss"
        log_entry["pnl"] = profit
        log_entry["timestamp"] = datetime.utcnow().isoformat()
        
        with open("trades.log", "a") as f:
            f.write(json.dumps(log_entry) + "\n")
            f.flush()  # Force write to disk immediately
        
        result = "WON" if won else "LOST"
        print(f"🔔 Trade {trade_id} {result}: ${profit:.2f}")
        
    except Exception as e:
        print(f"❌ Monitor error for {trade_id}: {e}")
    finally:
        # Always cleanup regardless of success/failure
        if asset in active_trades:
            del active_trades[asset]
        check_and_reset_trades()

def check_and_reset_trades():
    """Reset active trades counter when all trades are closed"""
    global active_trades
    
    # Force cleanup if trades exceed max concurrent (stuck state)
    if len(active_trades) > MAX_CONCURRENT:
        print(f"⚠️ FORCE RESET: {len(active_trades)} > {MAX_CONCURRENT} - clearing stuck trades")
        active_trades.clear()
        return
    
    if len(active_trades) == 0:
        print(f"🔄 All trades closed - Reset to 0/{MAX_CONCURRENT}")

def force_cleanup_expired_trades():
    """Force cleanup of trades that should have expired"""
    global active_trades
    if len(active_trades) > 0:
        print(f"🔄 Force cleaning {len(active_trades)} potentially stuck trades")
        
        # Log expired trades as losses before cleanup
        for asset, trade_id in active_trades.items():
            expired_log = {
                "id": trade_id,
                "strategy": "unknown",
                "timestamp": datetime.utcnow().isoformat(),
                "asset": asset,
                "direction": "unknown",
                "amount": 0,
                "duration": TIMEFRAME,
                "status": "expired",
                "pnl": 0
            }
            with open("trades.log", "a") as f:
                f.write(json.dumps(expired_log) + "\n")
                f.flush()
        
        active_trades.clear()
        print(f"✅ Active trades forcefully reset to 0/{MAX_CONCURRENT}")

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

async def wait_for_half_time():
    """Wait until half of current candle time has passed"""
    now = int(time.time())
    candle_progress = now % TIMEFRAME
    half_time = TIMEFRAME // 2
    
    if candle_progress < half_time:
        remaining = half_time - candle_progress
        print(f"⏰ Waiting {remaining}s for half-time...")
        for _ in range(remaining):
            if shutdown_requested or os.path.exists("STOP"):
                return False
            await asyncio.sleep(1)
    
    return True

async def main():
    global active_trades, failed_assets, trade_semaphore, shortlisted_assets, engulfing_candles_cache
    
    # Initialize semaphore
    trade_semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    last_connection_check = 0
    
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
    last_asset_refresh = time.time()
    print(f"🎯 Tradable assets: {len(tradable_assets)}")
    
    # Wait for next candle boundary
    await wait_for_candle_close()
    
    while True:
        # Check shutdown
        if shutdown_requested or os.path.exists("STOP"):
            break
        
        # Check connection status every 30 seconds
        current_time = time.time()
        if current_time - last_connection_check > 30:
            try:
                # Test connection by getting balance
                balance = await client.get_balance()
                if balance is None:
                    print("⚠️ Connection lost - attempting reconnect...")
                    connected, reason = await client.connect()
                    if connected:
                        print("✅ Reconnected successfully")
                        # Force asset refresh after reconnection
                        tradable_assets = await get_payout_filtered_assets(client, all_assets, PAYOUT_THRESHOLD)
                        last_asset_refresh = time.time()
                        print(f"🎯 Refreshed assets after reconnect: {len(tradable_assets)}")
                    else:
                        print(f"❌ Reconnection failed: {reason}")
                last_connection_check = current_time
            except Exception as e:
                print(f"⚠️ Connection check failed: {e}")
                last_connection_check = current_time
        
        # Refresh tradable assets every 5 minutes or if empty
        if time.time() - last_asset_refresh > 300 or len(tradable_assets) == 0:  # 5 minutes
            print("🔄 Refreshing tradable assets...")
            try:
                new_assets = await get_payout_filtered_assets(client, all_assets, PAYOUT_THRESHOLD)
                if new_assets:  # Only update if we got valid results
                    tradable_assets = new_assets
                    last_asset_refresh = time.time()
                    print(f"🎯 Updated tradable assets: {len(tradable_assets)}")
                else:
                    print("⚠️ Asset refresh returned empty - keeping previous list")
            except Exception as e:
                print(f"❌ Asset refresh failed: {e} - keeping previous list")
        
        # Clear failed assets more frequently (every 2 minutes)
        if len(failed_assets) > 0 and int(time.time()) % 120 == 0:  # Every 2 minutes
            failed_assets.clear()
            print("🔄 Cleared failed assets")
        
        # Sync check for active trades reset
        check_and_reset_trades()
        
        # Force cleanup every 5 minutes to prevent stuck trades
        if int(time.time()) % 300 == 0:  # Every 5 minutes
            force_cleanup_expired_trades()
        
        print(f"\n📊 ANALYZING | Active trades: {len(active_trades)}/{MAX_CONCURRENT}")
        
        # Filter available assets
        available_assets = [asset for asset in tradable_assets 
                          if asset not in active_trades and asset not in failed_assets]
        
        if len(active_trades) >= MAX_CONCURRENT:
            print("⏸️ Max concurrent trades reached - waiting for trades to close...")
            await asyncio.sleep(10)  # Wait 10 seconds before checking again
        elif not available_assets:
            print("❌ No available assets")
            # Force asset refresh if we have no available assets
            if len(tradable_assets) == 0:
                print("🔄 Force refreshing assets due to empty list...")
                try:
                    tradable_assets = await get_payout_filtered_assets(client, all_assets, PAYOUT_THRESHOLD)
                    last_asset_refresh = time.time()
                    print(f"🎯 Force refresh result: {len(tradable_assets)} assets")
                except Exception as e:
                    print(f"❌ Force refresh failed: {e}")
            await wait_for_candle_close()  # Wait for next cycle
        else:
            # Phase 0: Prefetch candles for engulfing at candle start
            await prefetch_engulfing_candles(client, available_assets)
            
            # Phase 1: Wait for half-time and prefilter breakout assets
            if BREAKOUT_ENABLED:
                if await wait_for_half_time():
                    await prefilter_breakout_assets(client, available_assets)
            
            # Phase 2: Wait for candle close and analyze
            await wait_for_candle_close()
            
            if shutdown_requested or os.path.exists("STOP"):
                break
            
            # Phase 3: Parallel analysis and immediate trading
            start_time = time.time()
            
            # Filter assets based on prefiltering results
            analysis_assets = []
            
            # Only add breakout shortlisted assets
            if BREAKOUT_ENABLED and shortlisted_assets:
                analysis_assets.extend(shortlisted_assets.keys())
                print(f"🎯 Breakout candidates: {list(shortlisted_assets.keys())}")
            
            # Only add engulfing cached assets that aren't already in breakout list
            if ENGULFING_ENABLED and engulfing_candles_cache:
                engulfing_only = [asset for asset in engulfing_candles_cache.keys() 
                                if asset not in analysis_assets]
                analysis_assets.extend(engulfing_only)
                print(f"🎯 Engulfing candidates: {engulfing_only}")
            
            # Filter out active/failed assets
            analysis_assets = [asset for asset in analysis_assets 
                             if asset not in active_trades and asset not in failed_assets]
            
            print(f"🎯 Final analysis list: {analysis_assets}")
            
            if analysis_assets:
                print(f"🔍 Analyzing {len(analysis_assets)} prefiltered assets: {analysis_assets}")
                
                # Create tasks for parallel analysis and trading
                tasks = [analyze_and_trade(client, asset, trade_amount) for asset in analysis_assets]
                
                # Execute all tasks concurrently with timeout
                try:
                    results = await asyncio.wait_for(
                        asyncio.gather(*tasks, return_exceptions=True),
                        timeout=5.0  # Reduced timeout since assets are prefiltered
                    )
                    
                    trades_placed = sum(1 for result in results if result is True)
                    analysis_time = time.time() - start_time
                    
                    print(f"✅ Analysis completed in {analysis_time:.1f}s | Trades placed: {trades_placed}")
                    
                except asyncio.TimeoutError:
                    analysis_time = time.time() - start_time
                    print(f"⏰ Analysis timeout after {analysis_time:.1f}s")
            else:
                print("❌ No prefiltered assets to analyze")
                print(f"Debug: Breakout shortlisted: {len(shortlisted_assets)}, Engulfing cached: {len(engulfing_candles_cache)}")
                await wait_for_candle_close()  # Wait for next cycle
        
        # Continue to next cycle
        await asyncio.sleep(1)  # Small delay to prevent tight loops
    
    print("🏁 Bot finished")
    
    # Cleanup
    if os.path.exists("STOP"):
        os.remove("STOP")

if __name__ == "__main__":
    asyncio.run(main())