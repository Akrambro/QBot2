from typing import List
from pyquotex.stable_api import Quotex

def get_payout_filtered_assets(client: Quotex, assets: List[str], payout_threshold: float) -> List[str]:
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
                payout = float(payout_value.get("1", 0))
            elif payout_value is not None:
                payout = float(payout_value)

            if payout >= payout_threshold:
                tradable_assets.append(asset_name)
        except (ValueError, TypeError) as e:
            print(f"Could not parse payout for {asset_name}: {e}")
            continue
    return tradable_assets
