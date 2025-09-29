import os
import time
import asyncio
from typing import List, Dict, Tuple

from dotenv import load_dotenv
from pyquotex.stable_api import Quotex


load_dotenv()


PAYOUT_THRESHOLD = float(os.getenv("QX_PAYOUT", "84"))
ASSET_LIST = os.getenv("QX_ASSETS", "EURUSD,GBPUSD,USDJPY,USDCHF,USDCAD,AUDUSD,EURGBP,EURJPY").split(",")
ASSET_LIST = [a.strip() for a in ASSET_LIST if a.strip()]
TIMEFRAME = int(os.getenv("QX_TIMEFRAME", "60"))  # seconds
TRADE_PERCENT = float(os.getenv("QX_TRADE_PERCENT", "2")) / 100.0
ACCOUNT_MODE = os.getenv("QX_ACCOUNT", "PRACTICE").upper()

# Loop config
RUN_MINUTES = int(os.getenv("QX_RUN_MINUTES", "0"))  # 0 means run indefinitely
PAYOUT_REFRESH_MIN = int(os.getenv("QX_PAYOUT_REFRESH_MIN", "10"))


def compute_signal(candles: List[Dict]) -> Tuple[str, bool]:
    if len(candles) < 6:
        return "", False

    prev = candles[-2]
    curr = candles[-1]
    window = candles[-6:-1]

    prev_low = float(prev["low"])
    prev_high = float(prev["high"])
    curr_close = float(curr["close"])

    lows = [float(c["low"]) for c in window]
    highs = [float(c["high"]) for c in window]

    if prev_low == min(lows) and curr_close > float(prev["high"]):
        return "call", True

    if prev_high == max(highs) and curr_close < float(prev["low"]):
        return "put", True

    return "", False


async def get_payout_filtered_assets(client: Quotex, assets: List[str]) -> List[str]:
    await client.get_instruments()
    payouts = []
    for asset in assets:
        try:
            profit = client.get_payout_by_asset(asset, timeframe="1")
            if profit is None:
                continue
            if isinstance(profit, dict):
                val = profit.get("1M") or profit.get("1")
                payout = float(val) if val is not None else 0.0
            else:
                payout = float(profit)
            if payout >= PAYOUT_THRESHOLD:
                payouts.append(asset)
        except Exception:
            continue
    return payouts


async def fetch_last_candles(client: Quotex, asset: str, timeframe: int, count: int) -> List[Dict]:
    end_from_time = time.time()
    seconds = timeframe * count
    candles = await client.get_candles(asset, end_from_time, seconds, timeframe)
    return candles or []


async def wait_next_candle_open(timeframe: int):
    now = int(time.time())
    remaining = timeframe - (now % timeframe)
    await asyncio.sleep(remaining + 0.05)


async def main():
    email = os.getenv("QX_EMAIL")
    password = os.getenv("QX_PASSWORD")

    client = Quotex(email=email, password=password, lang="en")
    client.set_account_mode("REAL" if ACCOUNT_MODE == "REAL" else "PRACTICE")
    connected, _ = await client.connect()
    if not connected:
        raise SystemExit("Failed to connect")

    end_time = None if RUN_MINUTES == 0 else time.time() + RUN_MINUTES * 60
    last_payout_refresh = 0.0
    tradable_assets: List[str] = []

    balance = await client.get_balance()
    trade_amount = round(max(balance * TRADE_PERCENT, 1.0), 2)
    print(f"Loop start | Mode={ACCOUNT_MODE} Balance={balance} Amount={trade_amount} Timeframe={TIMEFRAME}s Run={RUN_MINUTES}m")

    # Align to next candle to start evaluations
    await wait_next_candle_open(TIMEFRAME)

    while True:
        if end_time and time.time() >= end_time:
            break
        # graceful stop via STOP file
        if os.path.exists("STOP"):
            print("STOP file detected. Exiting loop.")
            break
        # refresh payout filter periodically
        if time.time() - last_payout_refresh > PAYOUT_REFRESH_MIN * 60 or not tradable_assets:
            tradable_assets = await get_payout_filtered_assets(client, ASSET_LIST)
            last_payout_refresh = time.time()
            print(f"Payout-filtered assets: {tradable_assets}")

        # fetch and evaluate each asset; place at most one trade per asset per candle
        for asset in tradable_assets:
            candles = await fetch_last_candles(client, asset, TIMEFRAME, 60 * 5)
            signal, ok = compute_signal(candles)
            if not ok:
                continue

            print(f"Signal {signal.upper()} on {asset}. Waiting for next open...")
            await wait_next_candle_open(TIMEFRAME)
            success, payload = await client.buy(
                amount=trade_amount,
                asset=asset,
                direction=signal,
                duration=TIMEFRAME,
                time_mode="TIME",
            )
            print("Placed:", success, payload)
        # Wait for next candle boundary before next evaluation round
        await wait_next_candle_open(TIMEFRAME)

    print("Loop finished.")


if __name__ == "__main__":
    asyncio.run(main())


