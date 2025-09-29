import os
import json
import signal
import shutil
import asyncio
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, validator


ROOT = Path(__file__).parent
VENV_PY = ROOT / ".venv" / "Scripts" / "python.exe"
STRATEGY = ROOT / "strategy_breakout_loop.py"
STOP_FILE = ROOT / "STOP"


class StartSettings(BaseModel):
    payout: float = Field(84, ge=0, le=100)
    assets: str = Field("EURUSD,GBPUSD,USDJPY,USDCHF,USDCAD,AUDUSD,EURGBP,EURJPY")
    timeframe: int = Field(60, ge=15, le=3600)
    trade_percent: float = Field(2.0, ge=0.5, le=15.0)
    account: str = Field("PRACTICE")  # PRACTICE | REAL
    max_concurrent: int = Field(1, ge=1, le=10)
    run_minutes: int = Field(0, ge=0)  # 0 => indefinite
    payout_refresh_min: int = Field(10, ge=1, le=120)
    daily_profit_limit: float = Field(0)  # 0 => disabled
    daily_profit_is_percent: bool = Field(True)
    daily_loss_limit: float = Field(0)  # 0 => disabled
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


def build_env(settings: StartSettings) -> Dict[str, str]:
    env = os.environ.copy()
    env.update({
        "QX_PAYOUT": str(settings.payout),
        "QX_ASSETS": settings.assets,
        "QX_TIMEFRAME": str(settings.timeframe),
        "QX_TRADE_PERCENT": str(settings.trade_percent),
        "QX_ACCOUNT": settings.account,
        "QX_RUN_MINUTES": str(settings.run_minutes),
        "QX_PAYOUT_REFRESH_MIN": str(settings.payout_refresh_min),
        # Optional risk controls for future enhancement
        "QX_DAILY_PROFIT": str(settings.daily_profit_limit),
        "QX_DAILY_PROFIT_IS_PERCENT": "1" if settings.daily_profit_is_percent else "0",
        "QX_DAILY_LOSS": str(settings.daily_loss_limit),
        "QX_DAILY_LOSS_IS_PERCENT": "1" if settings.daily_loss_is_percent else "0",
        # Concurrency note (not yet enforced in loop)
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

    # Ensure STOP file absent
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
        current_settings = json.loads(settings.json())
        return {"ok": True}
    except Exception as exc:
        raise HTTPException(500, detail=f"Failed to start: {exc}")


@app.post("/api/stop")
async def stop_bot():
    global process
    # Signal graceful stop
    STOP_FILE.write_text("stop")
    await asyncio.sleep(1.0)
    # If still alive, terminate
    if process and process.poll() is None:
        try:
            if os.name == "nt":
                process.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
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


