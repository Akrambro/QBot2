import os
import asyncio
from dotenv import load_dotenv

from quotexpy import Quotex


def str_to_bool(value: str) -> bool:
    return str(value).lower() in ["1", "true", "yes", "y", "on"]


async def main() -> None:
    load_dotenv()

    email = os.getenv("QX_EMAIL")
    password = os.getenv("QX_PASSWORD")
    browser_flag = str_to_bool(os.getenv("QX_BROWSER", "true"))
    pin_env = os.getenv("QX_PIN")

    if not email or not password:
        raise SystemExit("Missing QX_EMAIL or QX_PASSWORD in .env")

    def on_pin_code():
        if pin_env:
            return pin_env
        # Fallback: ask user in console if available
        try:
            return input("Enter Quotex PIN/2FA code: ")
        except Exception:
            raise RuntimeError("QX_PIN not set and interactive input unavailable")

    client = Quotex(
        email=email,
        password=password,
        browser=browser_flag,
        headless=False,
        on_pin_code=on_pin_code,
        wait_for_user=True,
    )

    try:
        connected = await client.connect()
        if not connected:
            raise RuntimeError("Login failed")
        balance = await client.get_balance()
        print(f"Connected. Balance: {balance}")
    except Exception as exc:
        print(f"Connection failed: {exc}")
        raise


if __name__ == "__main__":
    asyncio.run(main())


