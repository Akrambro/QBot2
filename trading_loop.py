import os
import time
import asyncio
import json
import signal
import logging
from datetime import datetime
from typing import List, Dict, Optional

from dotenv import load_dotenv
from pyquotex.stable_api import Quotex

from assets import live_assets, otc_assets
from utils import get_payout_filtered_assets
from strategies.breakout_strategy import check_extremes_condition, compute_breakout_signal
from strategies.engulfing_strategy import compute_engulfing_signal
from strategies.bollinger_break import compute_bollinger_break_signal

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
PAYOUT_THRESHOLD = float(os.getenv("QX_PAYOUT", "84"))
TRADE_PERCENT = float(os.getenv("QX_TRADE_PERCENT", "2")) / 100.0
ACCOUNT_MODE = os.getenv("QX_ACCOUNT", "PRACTICE").upper()
MAX_CONCURRENT = int(os.getenv("QX_MAX_CONCURRENT", "1"))
TIMEFRAME = int(os.getenv("QX_TIMEFRAME", "60"))
BREAKOUT_ENABLED = os.getenv("QX_BREAKOUT_ENABLED", "1") == "1"
ENGULFING_ENABLED = os.getenv("QX_ENGULFING_ENABLED", "1") == "1"
BOLLINGER_ENABLED = os.getenv("QX_BOLLINGER_ENABLED", "0") == "1"
BOLLINGER_PERIOD = int(os.getenv("QX_BOLLINGER_PERIOD", "14"))
BOLLINGER_DEVIATION = float(os.getenv("QX_BOLLINGER_DEVIATION", "1.0"))

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
    """
    Fetch candles using PyQuotex get_candles() API.
    Corrected to use proper API signature that works in practice.
    """
    try:
        api_asset = asset.replace('/', '').replace(' (OTC)', '_otc')
        
        # Step 1: Verify asset is available and market is open
        asset_name, asset_data = await client.get_available_asset(api_asset, force_open=True)
        if not asset_data or not asset_data[2]:  # asset_data[2] = is_open boolean
            logger.warning(f"{asset}: Asset not available or market closed")
            return None
        
        # Step 2: Use get_candles() with correct signature
        # API signature: get_candles(asset, end_from_time, offset, period)
        # offset = seconds of historical data
        # IMPORTANT: Need at least 30 candles for strategies (30 * TIMEFRAME)
        end_time = int(time.time())
        offset = TIMEFRAME * 50  # Request 50 candles worth (will get 20-30 typically)
        period = TIMEFRAME  # Candle period in seconds (60, 120, etc.)
        
        candles = await client.get_candles(asset_name, end_time, offset, period)
        
        # Validate we got candles
        if not candles or len(candles) == 0:
            logger.warning(f"{asset}: No candles returned")
            return None
        
        # Keep the most recent 30 candles (strategies need 20+ for trend analysis)
        if len(candles) > 30:
            candles = candles[-30:]
        
        # Check if we have enough candles for strategies
        if len(candles) < 20:
            logger.warning(f"{asset}: Only got {len(candles)} candles - strategies need 20+")
            # Don't return None - try to work with what we have
            # Some strategies might still work with fewer candles
        
        logger.info(f"[OK] {asset}: Fetched {len(candles)} candles")
        
        # Normalize candle data - pyquotex returns 'high'/'low' but strategies expect 'max'/'min'
        normalized_candles = []
        for i, candle in enumerate(candles):
            # Check which key format is being used
            has_max_min = 'max' in candle and 'min' in candle
            has_high_low = 'high' in candle and 'low' in candle
            has_open_close = 'open' in candle and 'close' in candle
            
            # Need at least OHLC in some format
            if not has_open_close:
                logger.warning(f"{asset}: Missing open/close in candle {i+1}/{len(candles)}")
                continue  # Skip bad candle, don't fail entire fetch
                
            if not has_max_min and not has_high_low:
                logger.warning(f"{asset}: Missing high/low in candle {i+1}/{len(candles)}")
                continue  # Skip bad candle
            
            # Create normalized candle with both formats for compatibility
            normalized = dict(candle)
            if has_high_low and not has_max_min:
                normalized['max'] = candle['high']
                normalized['min'] = candle['low']
            elif has_max_min and not has_high_low:
                normalized['high'] = candle['max']
                normalized['low'] = candle['min']
            
            # Validate price data
            try:
                o = float(normalized.get('open', 0))
                c = float(normalized.get('close', 0))
                h = float(normalized.get('max') or normalized.get('high', 0))
                l = float(normalized.get('min') or normalized.get('low', 0))
                
                # Only reject candles with obviously corrupt data
                if any(val <= 0 for val in [o, c, h, l]):
                    logger.debug(f"{asset}: Skipping candle {i+1}/{len(candles)} - zero/negative price")
                    continue
                
                # Allow minor OHLC violations (could be data feed quirks)
                # Only reject if high < low (impossible scenario)
                if h < l:
                    logger.debug(f"{asset}: Skipping candle {i+1}/{len(candles)} - high < low")
                    continue
                
                # Auto-correct minor OHLC relationship issues
                if h < max(o, c):
                    h = max(o, c)
                    normalized['max'] = h
                    normalized['high'] = h
                if l > min(o, c):
                    l = min(o, c)
                    normalized['min'] = l
                    normalized['low'] = l
                        
            except (ValueError, TypeError) as e:
                logger.debug(f"{asset}: Skipping candle {i+1}/{len(candles)} - invalid data type")
                continue
            
            normalized_candles.append(normalized)
        
        # Make sure we have enough valid candles
        if len(normalized_candles) < 6:
            logger.warning(f"{asset}: Insufficient valid candles - got {len(normalized_candles)}, need 6+")
            return None
        
        logger.info(f"[OK] {asset}: Validated {len(normalized_candles)} candles (passed OHLC checks)")
        return normalized_candles
        
    except Exception as e:
        logger.error(f"{asset}: Candle fetch error - {type(e).__name__}: {e}")
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
    """
    Analyze single asset for all strategies and return signal if found.
    ALWAYS fetches fresh candles to ensure we analyze the most recent CLOSED candle.
    """
    if asset in active_trades or asset in failed_assets:
        return None
    
    # Fetch fresh candles immediately - includes the candle that JUST CLOSED
    candles = await fetch_candles(client, asset)
    if not candles or len(candles) < 6:
        return None
    
    # Check breakout strategy
    if BREAKOUT_ENABLED:
        # Compute extremes on-the-fly (fast enough)
        from strategies.breakout_strategy import check_extremes_condition
        is_low_extreme, is_high_extreme = check_extremes_condition(candles)
        
        if is_low_extreme or is_high_extreme:
            extremes = (is_low_extreme, is_high_extreme)
            signal, valid, msg = compute_breakout_signal(candles, extremes)
            if valid:
                print(f"✅ {asset} BREAKOUT SIGNAL: {signal.upper()} - {msg}")
                return {
                    "asset": asset,
                    "signal": signal,
                    "strategy": "breakout"
                }
    
    # Check engulfing strategy
    if ENGULFING_ENABLED:
        signal, valid, msg = compute_engulfing_signal(candles)
        if valid:
            print(f"✅ {asset} ENGULFING SIGNAL: {signal.upper()} - {msg}")
            return {
                "asset": asset,
                "signal": signal,
                "strategy": "engulfing"
            }
    
    # Check Bollinger Break strategy
    if BOLLINGER_ENABLED and len(candles) >= BOLLINGER_PERIOD + 1:
        signal, valid, msg = compute_bollinger_break_signal(
            candles, 
            period=BOLLINGER_PERIOD, 
            deviation=BOLLINGER_DEVIATION
        )
        if valid:
            print(f"✅ {asset} BOLLINGER BREAK SIGNAL: {signal.upper()} - {msg}")
            return {
                "asset": asset,
                "signal": signal,
                "strategy": "bollinger_break"
            }
    
    return None

async def analyze_and_trade(client: Quotex, asset: str, trade_amount: float) -> bool:
    """Analyze asset and immediately place trade if signal found"""
    try:
        signal_data = await analyze_asset(client, asset, trade_amount)
        
        if signal_data:
            logger.info(f"[SIGNAL] {signal_data['strategy'].upper()} {signal_data['signal'].upper()}: {asset}")
            return await place_trade(client, signal_data, trade_amount)
        
        return False
    except Exception as e:
        logger.error(f"{asset}: Analysis error - {type(e).__name__}: {e}", exc_info=True)
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
            
            # Verify asset is available and open before placing trade
            try:
                asset_name, asset_data = await client.get_available_asset(api_asset, force_open=True)
                if not asset_data or not asset_data[2]:  # asset_data[2] = is_open
                    logger.warning(f"{asset}: Market closed or asset unavailable - skipping trade")
                    print(f"⚠️ {asset}: Market closed - cannot place trade")
                    return False
            except Exception as e:
                logger.warning(f"{asset}: Asset verification failed - {e}")
                # Continue anyway - might be API issue
            
            success, payload = await asyncio.wait_for(
                client.buy(
                    amount=trade_amount,
                    asset=api_asset,
                    direction=signal.lower(),  # PyQuotex requires lowercase 'call'/'put'
                    duration=TIMEFRAME
                ),
                timeout=5.0
            )
            
            if success and payload.get("id"):
                trade_id = payload["id"]
                active_trades[asset] = trade_id
                
                # Enhanced logging with strategy-specific details
                if strategy == "bollinger_break":
                    print(f"🎯 BOLLINGER BREAK TRADE PLACED!")
                    print(f"   Asset: {asset}")
                    print(f"   Direction: {signal.upper()}")
                    print(f"   Amount: ${trade_amount}")
                    print(f"   Trade ID: {trade_id}")
                    print(f"   BB Period: {BOLLINGER_PERIOD} | Deviation: {BOLLINGER_DEVIATION}")
                else:
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
                # Enhanced error logging to diagnose trade failures
                logger.error(f"{asset}: Trade placement FAILED")
                logger.error(f"  - Success flag: {success}")
                logger.error(f"  - Payload type: {type(payload)}")
                logger.error(f"  - Payload content: {payload}")
                logger.error(f"  - Asset (API format): {api_asset}")
                logger.error(f"  - Direction: {signal}")
                logger.error(f"  - Amount: {trade_amount}")
                logger.error(f"  - Duration: {TIMEFRAME}")
                
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
            profit = client.get_profit()  # Returns float directly, not async
        except asyncio.TimeoutError:
            logger.warning(f"{asset}: Monitor timeout for trade {trade_id} - forcing cleanup")
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
        logger.error(f"Monitor error for trade {trade_id}: {type(e).__name__}: {e}", exc_info=True)
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
    if BOLLINGER_ENABLED:
        print(f"📊 Bollinger Break: {BOLLINGER_ENABLED} | Period: {BOLLINGER_PERIOD} | Deviation: {BOLLINGER_DEVIATION}")
    
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
            # ⚡ TIMING FIX: Analyze IMMEDIATELY after candle close, place trade on NEW candle
            # Current candle just closed - this is the LAST CONFIRMED candle we analyze
            # Next candle is OPENING NOW - this is where we place our trade
            
            if shutdown_requested or os.path.exists("STOP"):
                break
            
            # Phase 1: Parallel analysis and IMMEDIATE trading (on fresh candle)
            start_time = time.time()
            
            # Analyze ALL available assets (no pre-filtering needed - fast enough now)
            print(f"🔍 Analyzing {len(available_assets)} available assets")
            
            if available_assets:
                # With ~15 tradable assets max, we can analyze all without batching
                # Each asset needs ~0.3-0.5s (fetch + analyze)
                # Total: 15 assets × 0.5s = ~7.5 seconds typical
                
                print(f"🔍 Analyzing {len(available_assets)} assets in parallel...")
                
                # Create tasks for parallel analysis and trading
                tasks = [analyze_and_trade(client, asset, trade_amount) for asset in available_assets]
                
                # Generous timeout for up to 20 assets: 20 × 0.5s + 10s buffer = 20s
                timeout_seconds = max(20.0, len(available_assets) * 1.0)
                
                try:
                    results = await asyncio.wait_for(
                        asyncio.gather(*tasks, return_exceptions=True),
                        timeout=timeout_seconds
                    )
                    
                    trades_placed = sum(1 for result in results if result is True)
                    analysis_time = time.time() - start_time
                    
                    print(f"✅ Analysis completed in {analysis_time:.1f}s | Trades placed: {trades_placed}/{len(available_assets)}")
                    
                except asyncio.TimeoutError:
                    analysis_time = time.time() - start_time
                    print(f"⏰ Analysis timeout after {analysis_time:.1f}s")
                    print(f"   Tried {len(available_assets)} assets - some may be slow to respond")
            else:
                print("❌ No available assets to analyze")
            
            # Wait for next candle close to repeat
            await wait_for_candle_close()
        
        # Continue to next cycle
        await asyncio.sleep(1)  # Small delay to prevent tight loops
    
    print("🏁 Bot finished")
    
    # Cleanup
    if os.path.exists("STOP"):
        os.remove("STOP")

if __name__ == "__main__":
    asyncio.run(main())