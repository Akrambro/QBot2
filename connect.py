import os
import asyncio
from dotenv import load_dotenv

from pyquotex.stable_api import Quotex


def str_to_bool(value: str) -> bool:
    return str(value).lower() in ["1", "true", "yes", "y", "on"]


async def main() -> None:
    load_dotenv()

    email = os.getenv("QX_EMAIL")
    password = os.getenv("QX_PASSWORD")

    if not email or not password:
        raise SystemExit("Missing QX_EMAIL or QX_PASSWORD in .env")

    client = Quotex(email=email, password=password)

    try:
        connected, reason = await client.connect()
        if not connected:
            raise RuntimeError(f"Login failed: {reason}")
        balance = await client.get_balance()
        print(f"Connected. Balance: {balance}")
    except Exception as exc:
        print(f"Connection failed: {exc}")
        raise


if __name__ == "__main__":
    asyncio.run(main())


