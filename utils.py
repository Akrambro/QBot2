from typing import List
from pyquotex.stable_api import Quotex
import asyncio


async def get_payout_filtered_assets(client: Quotex, assets: List[str], payout_threshold: float) -> List[str]:
    try:
        print(f"🔍 Filtering {len(assets)} assets with {payout_threshold}% threshold")
        all_payments = client.get_payment()
        
        if not all_payments:
            print("❌ No payment data received from Quotex")
            return []
        
        print(f"✅ Got payment data for {len(all_payments)} total assets")
        tradable_assets = []
        
        for asset_name in assets:
            try:
                payment_info = all_payments.get(asset_name)
                if not payment_info:
                    continue
                    
                is_open = payment_info.get("open", False)
                if not is_open:
                    continue

                # Extract payout from profit field (use 1M timeframe)
                profit_value = payment_info.get('profit', {})
                payout = 0
                
                if isinstance(profit_value, dict):
                    # Try 1M first, then 5M as fallback
                    payout = profit_value.get('1M', profit_value.get('5M', 0))
                
                # Convert to float
                try:
                    payout = float(payout)
                except (ValueError, TypeError):
                    payout = 0
                    
                if payout >= payout_threshold:
                    tradable_assets.append(asset_name)
                    print(f"✅ {asset_name}: {payout}% (✓ above {payout_threshold}%)")
                else:
                    print(f"⚠️ {asset_name}: {payout}% (below {payout_threshold}%)")
                    
            except Exception as e:
                print(f"❌ Error processing {asset_name}: {e}")
                continue
        
        print(f"🎯 Found {len(tradable_assets)} tradable assets")
        if tradable_assets:
            print(f"Assets: {', '.join(tradable_assets)}")
        return sorted(tradable_assets)
        
    except Exception as e:
        print(f"❌ Error filtering assets: {e}")
        return []
