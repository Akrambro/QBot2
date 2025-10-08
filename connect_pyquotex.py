import os
import asyncio
from dotenv import load_dotenv
from pyquotex.stable_api import Quotex


load_dotenv()

email = os.getenv('QX_EMAIL')
password = os.getenv('QX_PASSWORD')
account_mode = os.getenv('QX_ACCOUNT', 'PRACTICE').upper()  # PRACTICE or REAL


async def main():
    client = Quotex(email=email, password=password, lang='en')
    try:
        # select account type before connecting
        client.set_account_mode('REAL' if account_mode == 'REAL' else 'PRACTICE')
        connected, reason = await client.connect()
        if not connected:
            raise RuntimeError(f'Login failed: {reason}')
        balance = await client.get_balance()
        print(f'Connected via PyQuotex ({account_mode}). Balance: {balance}')
    except Exception as e:
        print(f'Connection failed: {e}')
        raise


if __name__ == '__main__':
    asyncio.run(main())