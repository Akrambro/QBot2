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

    prev_low = float(prev["low"])
    prev_high = float(prev["high"])
    curr_close = float(curr["close"])

    lows = [float(c["low"]) for c in window]
    highs = [float(c["high"]) for c in window]

    is_prev_low_lowest5 = prev_low == min(lows)
    is_prev_high_highest5 = prev_high == max(highs)

    # Upside condition
    if is_prev_low_lowest5 and curr_close > float(prev["high"]):
        return "call", True

    # Downside condition
    if is_prev_high_highest5 and curr_close < float(prev["low"]):
        return "put", True

    return "", False


def get_payout_filtered_assets(client: Quotex, assets: List[str]) -> List[str]:
    all_payments = client.get_payment()
    tradable_assets = []
    if not all_payments:
        print("Could not fetch payment data.")
        return tradable_assets

    for asset_name in assets:
        try:
            payment_info = all_payments.get(asset_name)
            if not payment_info or not payment_info.get("open"):
                continue

            payout_value = payment_info.get('payout')
            payout = 0
            if isinstance(payout_value, dict):
                # Using '1' for 1-minute timeframe as in old code
                payout = float(payout_value.get("1", 0))
            elif payout_value is not None:
                payout = float(payout_value)

            if payout >= PAYOUT_THRESHOLD:
                tradable_assets.append(asset_name)

        except (ValueError, TypeError) as e:
            print(f"Could not parse payout for {asset_name}: {e}. Data: {all_payments.get(asset_name)}")
            continue
        except Exception as e:
            print(f"An unexpected error occurred while processing payout for {asset_name}: {e}")
            continue

    return tradable_assets


async def fetch_last_candles(client: Quotex, asset: str, timeframe: int, count: int) -> List[Dict]:
    end_from_time = time.time()
    seconds = timeframe * count
    candles = await client.get_candles(asset, end_from_time, seconds, timeframe)
    return candles or []


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

    tradable_assets = get_payout_filtered_assets(client, ASSET_LIST)
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
        signal, valid = compute_signal(candles)
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


