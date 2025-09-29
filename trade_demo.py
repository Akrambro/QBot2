import os
import asyncio
from dotenv import load_dotenv
from pyquotex.stable_api import Quotex

load_dotenv()

email = os.getenv('QX_EMAIL')
password = os.getenv('QX_PASSWORD')
asset = os.getenv('QX_ASSET', 'EURUSD')
duration = int(os.getenv('QX_DURATION', '60'))  # seconds

async def main():
    client = Quotex(email=email, password=password, lang='en')
    # Ensure demo mode
    client.set_account_mode('PRACTICE')
    connected, _ = await client.connect()
    if not connected:
        raise SystemExit('Failed to connect')
    balance = await client.get_balance()
    amount = round(max(balance * 0.02, 1.0), 2)
    print(f'Demo balance: {balance}. Placing UP trade for {amount} on {asset} / {duration}s')
    ok, result = await client.buy(amount=amount, asset=asset, direction='call', duration=duration, time_mode='TIME')
    print('Trade status:', ok)
    print('Result payload:', result)

if __name__ == '__main__':
    asyncio.run(main())
