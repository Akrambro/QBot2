import os
import time
import asyncio
import json
from datetime import datetime
from typing import List, Dict, Tuple

from dotenv import load_dotenv
from pyquotex.stable_api import Quotex

from assets import live_assets, otc_assets
from strategies.engulfing_strategy import check_engulfing_signal
from strategies.strategy_breakout import check_breakout_signal
from utils import get_payout_filtered_assets


load_dotenv()


PAYOUT_THRESHOLD = float(os.getenv("QX_PAYOUT", "84"))
ASSET_LIST = live_assets + otc_assets
TIMEFRAME = int(os.getenv("QX_TIMEFRAME", "60"))  # seconds
TRADE_PERCENT = float(os.getenv("QX_TRADE_PERCENT", "2")) / 100.0
ACCOUNT_MODE = os.getenv("QX_ACCOUNT", "PRACTICE").upper()

# Loop config
RUN_MINUTES = int(os.getenv("QX_RUN_MINUTES", "0"))  # 0 means run indefinitely
PAYOUT_REFRESH_MIN = int(os.getenv("QX_PAYOUT_REFRESH_MIN", "10"))


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
    connected, reason = await client.connect()
    if not connected:
        raise SystemExit(f"Failed to connect: {reason}")

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
            tradable_assets = get_payout_filtered_assets(client, ASSET_LIST, PAYOUT_THRESHOLD)
            last_payout_refresh = time.time()
            print(f"Payout-filtered assets: {tradable_assets}")

        # fetch and evaluate each asset; place at most one trade per asset per candle
        for asset in tradable_assets:
            candles = await fetch_last_candles(client, asset, TIMEFRAME, 60 * 5)

            breakout_signal, breakout_ok = check_breakout_signal(candles)
            if breakout_ok:
                signal = breakout_signal
            else:
                engulfing_signal, engulfing_ok = check_engulfing_signal(candles)
                if engulfing_ok:
                    signal = engulfing_signal
                else:
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
            if success:
                try:
                    with open("trades.log", "a") as f:
                        log_entry = {
                            "id": payload.get("id", str(time.time())),
                            "timestamp": datetime.utcnow().isoformat(),
                            "asset": asset,
                            "direction": signal,
                            "amount": trade_amount,
                            "duration": TIMEFRAME,
                            "status": "active",
                            "pnl": 0, # To be updated later
                            "account_mode": ACCOUNT_MODE
                        }
                        f.write(json.dumps(log_entry) + "\n")
                except Exception as e:
                    print(f"Failed to write to trades.log: {e}")

        # Wait for next candle boundary before next evaluation round
        await wait_next_candle_open(TIMEFRAME)

    print("Loop finished.")


if __name__ == "__main__":
    asyncio.run(main())


