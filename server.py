import os
print("--- server.py execution started ---")
import json
import signal
import shutil
import asyncio
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any

from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv

from pyquotex.stable_api import Quotex
from assets import live_assets, otc_assets
from utils import get_payout_filtered_assets


ROOT = Path(__file__).parent
VENV_PY = ROOT / ".venv" / "Scripts" / "python.exe"
STRATEGY = ROOT / "strategy_breakout_loop.py"
STOP_FILE = ROOT / "STOP"


class StartSettings(BaseModel):
    payout: float = Field(84, ge=0, le=100)
    timeframe: int = Field(60, ge=15, le=3600)
    trade_percent: float = Field(2.0, ge=0.5, le=15.0)
    account: str = Field("PRACTICE")  # PRACTICE | REAL
    max_concurrent: int = Field(1, ge=1, le=10)
    run_minutes: int = Field(0, ge=0)  # 0 => indefinite
    payout_refresh_min: int = Field(10, ge=1, le=120)
    # The daily limit fields are now included in the settings
    daily_profit_limit: float = Field(0)
    daily_profit_is_percent: bool = Field(True)
    daily_loss_limit: float = Field(0)
    daily_loss_is_percent: bool = Field(True)

    @validator("account")
    def _acc(cls, v):
        v = v.upper()
        if v not in {"PRACTICE", "REAL"}:
            raise ValueError("account must be PRACTICE or REAL")
        return v


app = FastAPI()
app.mount("/", StaticFiles(directory=str(ROOT / "frontend"), html=True), name="static")


process: Optional[subprocess.Popen] = None
current_settings: Dict[str, Any] = {}


@app.get("/api/initial_data")
async def get_initial_data():
    load_dotenv()
    email = os.getenv("QX_EMAIL")
    password = os.getenv("QX_PASSWORD")

    if not email or not password:
        raise HTTPException(400, "Missing QX_EMAIL or QX_PASSWORD in .env")

    client = Quotex(email=email, password=password)
    practice_balance = 0
    real_balance = 0
    tradable_assets = []

    try:
        connected, reason = await client.connect()
        if not connected:
            raise HTTPException(500, detail=f"Failed to connect to Quotex: {reason}")

        # Fetch practice balance
        client.set_account_mode("PRACTICE")
        practice_balance = await client.get_balance()

        # Fetch real balance
        await client.change_account("REAL")
        real_balance = await client.get_balance()

        # Using a default payout of 84 for initial filtering
        tradable_assets = get_payout_filtered_assets(client, live_assets + otc_assets, 84)

    except Exception as e:
        print(f"An error occurred: {e}")
        # Don't raise HTTPException here to avoid breaking the frontend completely
    finally:
        await client.close()

    return {
        "balances": {
            "practice": practice_balance,
            "real": real_balance,
        },
        "assets": tradable_assets,
    }


@app.get("/api/trade_logs")
async def get_trade_logs():
    active_trades = []
    trade_history = []
    log_file = ROOT / "trades.log"
    if not log_file.exists():
        return {"active_trades": [], "trade_history": []}

    try:
        with open(log_file, "r") as f:
            lines = f.readlines()

        today_str = datetime.utcnow().date().isoformat()

        for line in reversed(lines):
            if not line.strip():
                continue
            try:
                log = json.loads(line)

                if log.get("timestamp", "").startswith(today_str):
                    if log.get("status") == "active":
                        log["live_pnl"] = "N/A"
                        active_trades.append(log)
                    else:
                        log["balance_after"] = "N/A"
                        trade_history.append(log)

            except json.JSONDecodeError:
                print(f"Skipping malformed log line: {line.strip()}")
                continue
    except Exception as e:
        print(f"Error reading or processing trades.log: {e}")

    return {"active_trades": active_trades, "trade_history": trade_history}


def build_env(settings: StartSettings) -> Dict[str, str]:
    env = os.environ.copy()
    env.update({
        "QX_PAYOUT": str(settings.payout),
        "QX_TIMEFRAME": str(settings.timeframe),
        "QX_TRADE_PERCENT": str(settings.trade_percent),
        "QX_ACCOUNT": str(settings.account),
        "QX_RUN_MINUTES": str(settings.run_minutes),
        "QX_PAYOUT_REFRESH_MIN": str(settings.payout_refresh_min),
        "QX_DAILY_PROFIT": str(settings.daily_profit_limit),
        "QX_DAILY_PROFIT_IS_PERCENT": "1" if settings.daily_profit_is_percent else "0",
        "QX_DAILY_LOSS": str(settings.daily_loss_limit),
        "QX_DAILY_LOSS_IS_PERCENT": "1" if settings.daily_loss_is_percent else "0",
        "QX_MAX_CONCURRENT": str(settings.max_concurrent),
    })
    return env


@app.post("/api/start")
async def start_bot(settings: StartSettings):
    global process, current_settings
    if not (ROOT / ".env").exists():
        raise HTTPException(400, detail="Missing .env with QX_EMAIL and QX_PASSWORD")
    if process and process.poll() is None:
        raise HTTPException(400, detail="Bot already running")

    if (ROOT / "trades.log").exists():
        (ROOT / "trades.log").unlink()

    if STOP_FILE.exists():
        STOP_FILE.unlink()

    env = build_env(settings)
    py = str(VENV_PY if VENV_PY.exists() else shutil.which("python"))
    if not py:
        raise HTTPException(500, detail="Python interpreter not found")

    try:
        process = subprocess.Popen(
            [py, str(STRATEGY)], cwd=str(ROOT), env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if hasattr(subprocess, 'CREATE_NEW_PROCESS_GROUP') else 0,
        )
        current_settings = json.loads(settings.dict())
        return {"ok": True}
    except Exception as exc:
        raise HTTPException(500, detail=f"Failed to start: {exc}")


@app.post("/api/stop")
async def stop_bot():
    global process
    STOP_FILE.write_text("stop")
    await asyncio.sleep(1.0)
    if process and process.poll() is None:
        try:
            if os.name == "nt":
                process.send_signal(signal.CTRL_BREAK_EVENT)
            process.terminate()
        except Exception:
            pass
    return {"ok": True}


@app.get("/api/status")
def status():
    running = bool(process and process.poll() is None)
    return {
        "running": running,
        "settings": current_settings,
    }
