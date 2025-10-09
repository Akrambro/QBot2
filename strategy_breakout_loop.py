import os
import time
import asyncio
import json
from datetime import datetime
from typing import List, Dict, Tuple, Optional

from dotenv import load_dotenv
from pyquotex.stable_api import Quotex

from assets import live_assets, otc_assets
from utils import get_payout_filtered_assets


load_dotenv()


PAYOUT_THRESHOLD = float(os.getenv("QX_PAYOUT", "84"))
ASSET_LIST = live_assets + otc_assets
ANALYSIS_TIMEFRAME = int(os.getenv("QX_ANALYSIS_TIMEFRAME", "60"))
TRADE_TIMEFRAME = int(os.getenv("QX_TRADE_TIMEFRAME", "60"))
TRADE_PERCENT = float(os.getenv("QX_TRADE_PERCENT", "2")) / 100.0
ACCOUNT_MODE = os.getenv("QX_ACCOUNT", "PRACTICE").upper()
MAX_CONCURRENT = int(os.getenv("QX_MAX_CONCURRENT", "1"))
RUN_MINUTES = int(os.getenv("QX_RUN_MINUTES", "0"))
PAYOUT_REFRESH_MIN = int(os.getenv("QX_PAYOUT_REFRESH_MIN", "10"))
DAILY_PROFIT_LIMIT = float(os.getenv("QX_DAILY_PROFIT", "0"))
DAILY_PROFIT_IS_PERCENT = os.getenv("QX_DAILY_PROFIT_IS_PERCENT") == "1"
DAILY_LOSS_LIMIT = float(os.getenv("QX_DAILY_LOSS", "0"))
DAILY_LOSS_IS_PERCENT = os.getenv("QX_DAILY_LOSS_IS_PERCENT") == "1"

# Global state
active_trade_count = 0
current_balance = 0
daily_pnl = 0


def compute_breakout_signal(candles: List[Dict]) -> Tuple[str, bool, str]:
    if len(candles) < 6:
        return "", False, "Insufficient candles"
    
    prev, curr = candles[-2], candles[-1]
    window = candles[-6:-1]
    
    prev_low, prev_high = float(prev["low"]), float(prev["high"])
    curr_close = float(curr["close"])
    
    min_low = min(float(c["low"]) for c in window)
    max_high = max(float(c["high"]) for c in window)
    
    if prev_low == min_low and curr_close > prev_high:
        return "call", True, "Breakout CALL"
    if prev_high == max_high and curr_close < prev_low:
        return "put", True, "Breakout PUT"
    
    return "", False, "No breakout"


def compute_engulfing_signal(candles: List[Dict]) -> Tuple[str, bool, str]:
    if len(candles) < 6:
        return "", False, "Insufficient candles"
    
    # Check for sideways market (alternating pattern)
    last_4 = candles[-4:]
    alternating = True
    for i in range(1, len(last_4)):
        curr_bullish = float(last_4[i]["close"]) > float(last_4[i]["open"])
        prev_bullish = float(last_4[i-1]["close"]) > float(last_4[i-1]["open"])
        if curr_bullish == prev_bullish:
            alternating = False
            break
    
    if alternating:
        return "", False, "Sideways market detected"
    
    prev, curr = candles[-2], candles[-1]
    
    prev_open, prev_close = float(prev["open"]), float(prev["close"])
    prev_high, prev_low = float(prev["high"]), float(prev["low"])
    
    curr_open, curr_close = float(curr["open"]), float(curr["close"])
    curr_high, curr_low = float(curr["high"]), float(curr["low"])
    
    # Check if current engulfs previous
    if not (curr_high > prev_high and curr_low < prev_low):
        return "", False, "No engulfing pattern"
    
    # Check candle strength (body vs wicks)
    body_size = abs(curr_close - curr_open)
    total_size = curr_high - curr_low
    if body_size <= 0.5 * total_size:
        return "", False, "Weak engulfing candle"
    
    # Bullish engulfing
    if curr_close > curr_open and prev_close < prev_open:
        return "call", True, "Engulfing CALL"
    
    # Bearish engulfing
    if curr_close < curr_open and prev_close > prev_open:
        return "put", True, "Engulfing PUT"
    
    return "", False, "No valid engulfing"


async def fetch_candles_fast(client: Quotex, asset: str) -> Optional[List[Dict]]:
    try:
        api_asset = asset.replace('/', '').replace(' (OTC)', '_otc')
        candles = await client.get_candles(api_asset, time.time(), ANALYSIS_TIMEFRAME * 60, ANALYSIS_TIMEFRAME)
        return candles if candles and len(candles) >= 6 else None
    except:
        return None


async def analyze_asset(client: Quotex, asset: str, trade_amount: float) -> Optional[Dict]:
    global active_trade_count
    
    # Check if we can place more trades
    if active_trade_count >= MAX_CONCURRENT:
        return None
        
    candles = await fetch_candles_fast(client, asset)
    if not candles:
        return None
    
    # Test both strategies
    breakout_signal, breakout_valid, breakout_msg = compute_breakout_signal(candles)
    engulfing_signal, engulfing_valid, engulfing_msg = compute_engulfing_signal(candles)
    
    if breakout_valid:
        return {
            "asset": asset,
            "signal": breakout_signal,
            "strategy": "breakout",
            "message": breakout_msg,
            "amount": trade_amount
        }
    
    if engulfing_valid:
        return {
            "asset": asset,
            "signal": engulfing_signal,
            "strategy": "engulfing",
            "message": engulfing_msg,
            "amount": trade_amount
        }
    
    return None


async def place_trade_fast(client: Quotex, trade_data: Dict) -> bool:
    global active_trade_count, current_balance
    
    try:
        api_asset = trade_data["asset"].replace('/', '').replace(' (OTC)', '_otc')
        success, payload = await client.buy(
            amount=trade_data["amount"],
            asset=api_asset,
            direction=trade_data["signal"],
            duration=TRADE_TIMEFRAME,
            time_mode="TIME"
        )
        
        if success and payload.get("id"):
            active_trade_count += 1
            current_balance -= trade_data["amount"]  # Deduct trade amount immediately
            
            print(f"✅ {trade_data['strategy'].upper()} {trade_data['signal'].upper()} on {trade_data['asset']} - ID: {payload['id']}")
            
            # Log trade
            log_entry = {
                "id": payload["id"],
                "strategy": trade_data["strategy"],
                "timestamp": datetime.utcnow().isoformat(),
                "asset": trade_data["asset"],
                "direction": trade_data["signal"],
                "amount": trade_data["amount"],
                "duration": TRADE_TIMEFRAME,
                "status": "active",
                "pnl": 0,
                "account_mode": ACCOUNT_MODE
            }
            
            with open("trades.log", "a") as f:
                f.write(json.dumps(log_entry) + "\n")
            
            # Start monitoring trade result
            asyncio.create_task(monitor_trade_result(client, payload["id"], log_entry))
            
            return True
        else:
            print(f"❌ Trade failed on {trade_data['asset']}: {payload}")
            return False
    except Exception as e:
        print(f"❌ Trade error on {trade_data['asset']}: {e}")
        return False

async def monitor_trade_result(client: Quotex, trade_id: str, log_entry: Dict):
    """Monitor trade result and update balance in real-time"""
    global active_trade_count, current_balance, daily_pnl
    
    try:
        # Wait for trade duration
        await asyncio.sleep(TRADE_TIMEFRAME + 5)
        
        # Check result
        won = await client.check_win(trade_id)
        profit = client.get_profit()
        
        # Update balance and PnL
        if won:
            # For winning trades, add back the original amount plus profit
            current_balance += log_entry["amount"] + profit
        else:
            # For losing trades, the amount was already deducted, profit is negative
            current_balance += profit  # This will be negative, further reducing balance
        
        daily_pnl += profit
        active_trade_count -= 1
        
        # Update log entry
        log_entry["status"] = "win" if won else "loss"
        log_entry["pnl"] = profit
        log_entry["timestamp"] = datetime.utcnow().isoformat()
        
        # Write final result
        with open("trades.log", "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        
        result = "WON" if won else "LOST"
        print(f"🔔 Trade {trade_id} {result}: ${profit:.2f} | Balance: ${current_balance:.2f} | Daily P&L: ${daily_pnl:.2f}")
        
    except Exception as e:
        print(f"❌ Error monitoring trade {trade_id}: {e}")
        active_trade_count = max(0, active_trade_count - 1)  # Ensure it doesn't go negative


def get_seconds_to_candle_close(timeframe: int) -> int:
    """Get seconds remaining until current candle closes"""
    now = int(time.time())
    return timeframe - (now % timeframe)

async def wait_for_55th_second(timeframe: int):
    """Wait until 55th second of current candle"""
    seconds_to_close = get_seconds_to_candle_close(timeframe)
    if seconds_to_close > 5:  # If more than 5 seconds to close
        wait_time = seconds_to_close - 5  # Wait until 5 seconds before close
        await asyncio.sleep(wait_time)

async def wait_next_candle_open(timeframe: int):
    now = int(time.time())
    remaining = timeframe - (now % timeframe)
    await asyncio.sleep(remaining + 0.05)


async def main():
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

    global current_balance, daily_pnl
    
    balance = await client.get_balance()
    current_balance = balance
    initial_balance = balance
    trade_amount = round(max(balance * TRADE_PERCENT, 1.0), 2)
    
    print(f"🚀 BOT STARTED | Mode: {ACCOUNT_MODE} | Balance: ${balance} | Trade: ${trade_amount}")
    print(f"📊 Strategies: Breakout + Engulfing | Max Concurrent: {MAX_CONCURRENT} | Timeframe: {ANALYSIS_TIMEFRAME}s")

    await wait_next_candle_open(ANALYSIS_TIMEFRAME)

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

        # Refresh assets
        if time.time() - last_payout_refresh > PAYOUT_REFRESH_MIN * 60 or not tradable_assets:
            tradable_assets = await get_payout_filtered_assets(client, ASSET_LIST, PAYOUT_THRESHOLD)
            last_payout_refresh = time.time()
            print(f"🎯 Assets: {len(tradable_assets)} | Balance: ${current_balance:.2f} | Daily P&L: ${daily_pnl:.2f}")

        # Wait for 55th second of current candle
        await wait_for_55th_second(ANALYSIS_TIMEFRAME)
        
        # Check if we have less than 5 seconds to candle close
        seconds_to_close = get_seconds_to_candle_close(ANALYSIS_TIMEFRAME)
        if seconds_to_close > 5:
            print(f"⏭️ Skipping - too early ({seconds_to_close}s to close)")
            await wait_next_candle_open(ANALYSIS_TIMEFRAME)
            continue
        
        print(f"⚡ Analyzing {len(tradable_assets)} assets ({seconds_to_close}s to close)...")
        
        # Create analysis tasks for all assets simultaneously (no timeout)
        analysis_tasks = [analyze_asset(client, asset, trade_amount) for asset in tradable_assets]
        results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
        
        # Filter valid signals
        valid_trades = [r for r in results if isinstance(r, dict) and r is not None]
        
        print(f"📊 Signals: {len(valid_trades)} | Active: {active_trade_count}/{MAX_CONCURRENT} | Balance: ${current_balance:.2f}")
        
        # Place trades immediately for all signals
        if valid_trades:
            trade_tasks = [place_trade_fast(client, trade) for trade in valid_trades]
            await asyncio.gather(*trade_tasks, return_exceptions=True)
        
        await wait_next_candle_open(ANALYSIS_TIMEFRAME)

    print("🏁 Bot finished")


if __name__ == "__main__":
    asyncio.run(main())


