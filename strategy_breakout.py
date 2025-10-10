import os
import time
import asyncio
from typing import List, Dict, Tuple

from dotenv import load_dotenv
from pyquotex.stable_api import Quotex

from assets import live_assets, otc_assets
from utils import get_payout_filtered_assets


load_dotenv()


PAYOUT_THRESHOLD = float(os.getenv("QX_PAYOUT", "84"))
ASSET_LIST = live_assets + otc_assets
TIMEFRAME = int(os.getenv("QX_TIMEFRAME", "60"))  # seconds
TRADE_PERCENT = float(os.getenv("QX_TRADE_PERCENT", "2")) / 100.0
ACCOUNT_MODE = os.getenv("QX_ACCOUNT", "PRACTICE").upper()


def compute_signal(candles: List[Dict]) -> Tuple[str, bool]:
    """Return (signal, valid) where signal is 'call'|'put'|''.

    Rules use the last 6 candles to evaluate:
    - previous = candles[-2]
    - current = candles[-1]
    - window for extremes: last 5 candles excluding current (candles[-6:-1])
    """
    if len(candles) < 6:
        return "", False

    prev = candles[-2]
    curr = candles[-1]
    window = candles[-6:-1]  # 5 candles ending at prev

    prev_open = float(prev["open"])
    prev_close = float(prev["close"])
    prev_low = float(prev["low"])
    prev_high = float(prev["high"])
    
    curr_open = float(curr["open"])
    curr_close = float(curr["close"])
    curr_high = float(curr["high"])
    curr_low = float(curr["low"])

    lows = [float(c["low"]) for c in window]
    highs = [float(c["high"]) for c in window]

    is_prev_low_lowest5 = prev_low == min(lows)
    is_prev_high_highest5 = prev_high == max(highs)

    # Upside CALL condition with filters
    if is_prev_low_lowest5 and curr_close > prev_high:
        # Filter: No close=high for green candles
        prev_is_green = prev_close > prev_open
        curr_is_green = curr_close > curr_open
        
       # if prev_is_green and prev_close == prev_high:
       #     return "", False  # Reject: Previous green candle close=high
       # if curr_is_green and curr_close == curr_high:
       #     return "", False  # Reject: Current green candle close=high
            
        return "call", True

    # Downside PUT condition with filters
    if is_prev_high_highest5 and curr_close < prev_low:
        # Filter: No close=low for red candles
        prev_is_red = prev_close < prev_open
        curr_is_red = curr_close < curr_open
        
        #if prev_is_red and prev_close == prev_low:
        #    return "", False  # Reject: Previous red candle close=low
        #    return "", False  # Reject: Current red candle close=low
            
        return "put", True

    return "", False


async def fetch_last_candles(client: Quotex, asset: str, timeframe: int, count: int) -> List[Dict]:
    try:
        end_from_time = time.time()
        seconds = timeframe * count
        # Convert asset name to API format
        api_asset = asset.replace('/', '').replace(' (OTC)', '_otc')
        candles = await client.get_candles(api_asset, end_from_time, seconds, timeframe)
        return candles or []
    except Exception as e:
        print(f"Candle fetch error for {asset}: {e}")
        return []


async def wait_next_candle_open(timeframe: int):
    now = int(time.time())
    remaining = timeframe - (now % timeframe)
    await asyncio.sleep(remaining + 0.05)


async def run_strategy_once():
    email = os.getenv("QX_EMAIL")
    password = os.getenv("QX_PASSWORD")

    client = Quotex(email=email, password=password, lang="en")
    client.set_account_mode("REAL" if ACCOUNT_MODE == "REAL" else "PRACTICE")
    connected, _ = await client.connect()
    if not connected:
        raise SystemExit("Failed to connect")

    tradable_assets = await get_payout_filtered_assets(client, ASSET_LIST, PAYOUT_THRESHOLD)
    if not tradable_assets:
        print("No assets meet payout threshold.")
        return

    balance = await client.get_balance()
    trade_amount = round(max(balance * TRADE_PERCENT, 1.0), 2)
    print(f"Mode={ACCOUNT_MODE} Balance={balance} Amount={trade_amount} Timeframe={TIMEFRAME}s")

    for asset in tradable_assets:
        candles = await fetch_last_candles(client, asset, TIMEFRAME, 60 * 5)  # up to 5h to be safe
        if len(candles) < 6:
            continue
        signal, valid, debug_info = compute_signal(candles, asset)
        if not valid:
            continue

        print(f"Signal {signal.upper()} on {asset}. Waiting next candle open...")
        await wait_next_candle_open(TIMEFRAME)
        ok, payload = await client.buy(
            amount=trade_amount,
            asset=asset,
            direction=signal,
            duration=TIMEFRAME,
            time_mode="TIME",
        )
        print("Placed:", ok, payload)
        return

    print("No signals this pass.")


if __name__ == "__main__":
    asyncio.run(run_strategy_once())
