import os
import json
import signal
import shutil
import asyncio
import subprocess
import secrets
from pathlib import Path
from typing import List, Optional, Dict, Any

from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv

from pyquotex.stable_api import Quotex
from assets import live_assets, otc_assets
from utils import get_payout_filtered_assets

# Global shutdown flag
shutdown_requested = False

def signal_handler(signum, frame):
    global shutdown_requested, process
    print(f"\n🛑 Server shutdown requested")
    shutdown_requested = True
    if process and process.poll() is None:
        try:
            process.terminate()
        except:
            pass
    os._exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


# Simple token-based authentication for localhost security
# Generate a random token on server startup
API_TOKEN = os.getenv("API_TOKEN", secrets.token_urlsafe(32))
print(f"🔐 API Token: {API_TOKEN}")
print(f"ℹ️  Add this to your .env file: API_TOKEN={API_TOKEN}")

security = HTTPBearer(auto_error=False)

async def verify_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """
    Verify API token for protected endpoints
    
    This provides basic security even for localhost deployments.
    The token is generated on startup and printed to console.
    """
    # For now, make authentication optional to maintain backward compatibility
    # In production, change this to raise HTTPException if token is invalid
    if credentials is None:
        # No token provided - allow for backward compatibility
        # TODO: Make this mandatory in future versions
        return True
    
    if credentials.credentials != API_TOKEN:
        raise HTTPException(
            status_code=401, 
            detail="Invalid authentication token"
        )
    
    return True


ROOT = Path(__file__).parent
VENV_PY = ROOT / ".venv" / "Scripts" / "python.exe"
STRATEGY = ROOT / "trading_loop.py"
STOP_FILE = ROOT / "STOP"


class StrategyConfig(BaseModel):
    enabled: bool = Field(True)
    analysis_timeframe: int = Field(60, ge=15, le=3600)
    trade_timeframe: int = Field(60, ge=15, le=3600)

class StartSettings(BaseModel):
    payout: float = Field(84, ge=0, le=100)
    trade_percent: float = Field(2.0, ge=0.5, le=15.0)
    account: str = Field("PRACTICE")  # PRACTICE | REAL
    max_concurrent: int = Field(1, ge=1, le=10)
    run_minutes: int = Field(0, ge=0)  # 0 => indefinite
    payout_refresh_min: int = Field(10, ge=1, le=120)
    # Strategy configurations
    breakout_strategy: StrategyConfig = Field(default_factory=lambda: StrategyConfig())
    engulfing_strategy: StrategyConfig = Field(default_factory=lambda: StrategyConfig())
    bollinger_strategy: StrategyConfig = Field(default_factory=lambda: StrategyConfig(enabled=False))
    # Bollinger-specific parameters
    bollinger_period: int = Field(14, ge=5, le=50)
    bollinger_deviation: float = Field(1.0, ge=0.5, le=3.0)
    # Daily limit fields
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

# CORS Configuration - Restrict to localhost for security
# Only allow requests from the same machine where the bot is running
ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost",
    "http://127.0.0.1",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # Restricted to localhost only
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Only allow necessary methods
    allow_headers=["Content-Type", "Authorization"],  # Specific headers only
    max_age=3600,  # Cache preflight requests for 1 hour
)


process: Optional[subprocess.Popen] = None
current_settings: Dict[str, Any] = {}


@app.get("/api/initial_data")
async def get_initial_data():
    load_dotenv()
    email = os.getenv("QX_EMAIL")
    password = os.getenv("QX_PASSWORD")

    if not email or not password:
        raise HTTPException(400, "Missing QX_EMAIL or QX_PASSWORD in .env")

    practice_balance = 0
    real_balance = 0
    tradable_assets = []

    # Retry logic for Cloudflare blocks
    max_retries = 2
    for attempt in range(max_retries):
        try:
            print(f"🔗 Connecting to Quotex (attempt {attempt + 1}/{max_retries})...")
            client = Quotex(email=email, password=password, lang="en")
            
            # Add random delay between attempts
            if attempt > 0:
                import random
                wait_time = random.randint(10, 30)  # Random 10-30s delay
                print(f"⏳ Waiting {wait_time}s to avoid detection...")
                await asyncio.sleep(wait_time)
            
            connected, reason = await client.connect()
        
            if not connected:
                if "403" in str(reason) or "Forbidden" in str(reason):
                    print(f"🚫 Cloudflare blocked (attempt {attempt + 1})")
                    if attempt < max_retries - 1:
                        continue  # Try again
                    else:
                        return {
                            "balances": {"practice": 0, "real": 0},
                            "assets": [],
                            "email": email,
                            "error": "Cloudflare protection. Wait 5-10 minutes and try again."
                        }
                else:
                    print(f"❌ Failed to connect to Quotex: {reason}")
                    return {
                        "balances": {"practice": 0, "real": 0},
                        "assets": [],
                        "email": email,
                        "error": f"Connection failed: {reason}"
                    }
        
            print("✅ Successfully connected to Quotex")

            # Fetch practice balance using change_account method
            print("💰 Fetching practice balance...")
            await client.change_account("PRACTICE")
            await asyncio.sleep(0.5)
            practice_balance = await client.get_balance()
            print(f"✅ Practice balance: ${practice_balance}")

            # Fetch real balance
            print("💰 Fetching real balance...")
            await client.change_account("REAL")
            await asyncio.sleep(0.5)
            real_balance = await client.get_balance()
            print(f"✅ Real balance: ${real_balance}")

            # Filter tradable assets
            print("🔍 Filtering tradable assets...")
            all_assets = live_assets + otc_assets
            tradable_assets = await get_payout_filtered_assets(client, all_assets, 84)
        
            await client.close()
            print("🔒 Connection closed")
            break  # Success, exit retry loop
            
        except Exception as e:
            error_msg = str(e)
            if "403" in error_msg or "Forbidden" in error_msg:
                print(f"🚫 Cloudflare detected (attempt {attempt + 1})")
                if attempt < max_retries - 1:
                    continue  # Try again
                else:
                    return {
                        "balances": {"practice": 0, "real": 0},
                        "assets": [],
                        "email": email,
                        "error": "Cloudflare protection. Wait and try again."
                    }
            else:
                print(f"❌ An error occurred: {e}")
                import traceback
                traceback.print_exc()
                return {
                    "balances": {"practice": 0, "real": 0},
                    "assets": [],
                    "email": email,
                    "error": str(e)
                }

    return {
        "balances": {
            "practice": practice_balance,
            "real": real_balance,
        },
        "assets": tradable_assets,
        "email": email,
        "daily_pnl": 0  # Initialize daily PnL
    }


@app.get("/api/trade_logs")
async def get_trade_logs():
    active_trades = []
    trade_history = []
    daily_pnl = 0
    log_file = ROOT / "trades.log"
    if not log_file.exists():
        return {"active_trades": [], "trade_history": [], "daily_pnl": 0}

    try:
        with open(log_file, "r") as f:
            lines = f.readlines()

        today_str = datetime.utcnow().date().isoformat()
        trade_states = {}  # Track latest state of each trade
        current_time = datetime.utcnow()

        # Process all lines to get latest state of each trade
        for line in lines:
            if not line.strip():
                continue
            try:
                log = json.loads(line)
                trade_id = log.get("id")
                
                if not trade_id or not log.get("timestamp", "").startswith(today_str):
                    continue
                
                trade_states[trade_id] = log

            except json.JSONDecodeError:
                continue
        
        # Separate active and completed trades
        for trade_id, log in trade_states.items():
            status = log.get("status")
            
            # Check if "active" trade has actually expired based on time
            if status == "active":
                try:
                    trade_time = datetime.fromisoformat(log.get("timestamp", "").replace("Z", "+00:00"))
                    duration = log.get("duration", 60)
                    expiry_time = trade_time.timestamp() + duration
                    current_timestamp = current_time.timestamp()
                    
                    # If trade has expired (current time > expiry + 10 sec buffer), treat as closed
                    if current_timestamp > expiry_time + 10:
                        # This trade should have been closed by now - skip it from active
                        # It will be updated to win/loss when monitor_trade completes
                        continue
                except (ValueError, TypeError):
                    pass
                
                # Still active - calculate time remaining
                log["live_pnl"] = "N/A"
                active_trades.append(log)
                
            elif status in ["win", "loss"]:
                log["balance_after"] = "N/A"
                trade_history.append(log)
                
                # Add to daily P&L
                pnl = log.get("pnl", 0)
                if isinstance(pnl, (int, float)):
                    daily_pnl += pnl
        
        # Sort trade history by timestamp (newest first) and limit to 30
        trade_history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        trade_history = trade_history[:30]
                    
    except Exception as e:
        print(f"Error reading or processing trades.log: {e}")

    return {"active_trades": active_trades, "trade_history": trade_history, "daily_pnl": daily_pnl}


def build_env(settings: StartSettings) -> Dict[str, str]:
    env = os.environ.copy()
    env.update({
        "QX_PAYOUT": str(settings.payout),
        "QX_TRADE_PERCENT": str(settings.trade_percent),
        "QX_ACCOUNT": str(settings.account),
        "QX_RUN_MINUTES": str(settings.run_minutes),
        "QX_PAYOUT_REFRESH_MIN": str(settings.payout_refresh_min),
        "QX_DAILY_PROFIT": str(settings.daily_profit_limit),
        "QX_DAILY_PROFIT_IS_PERCENT": "1" if settings.daily_profit_is_percent else "0",
        "QX_DAILY_LOSS": str(settings.daily_loss_limit),
        "QX_DAILY_LOSS_IS_PERCENT": "1" if settings.daily_loss_is_percent else "0",
        "QX_MAX_CONCURRENT": str(settings.max_concurrent),
        # Strategy configurations
        "QX_BREAKOUT_ENABLED": "1" if settings.breakout_strategy.enabled else "0",
        "QX_BREAKOUT_ANALYSIS_TF": str(settings.breakout_strategy.analysis_timeframe),
        "QX_BREAKOUT_TRADE_TF": str(settings.breakout_strategy.trade_timeframe),
        "QX_ENGULFING_ENABLED": "1" if settings.engulfing_strategy.enabled else "0",
        "QX_ENGULFING_ANALYSIS_TF": str(settings.engulfing_strategy.analysis_timeframe),
        "QX_ENGULFING_TRADE_TF": str(settings.engulfing_strategy.trade_timeframe),
        "QX_BOLLINGER_ENABLED": "1" if settings.bollinger_strategy.enabled else "0",
        "QX_BOLLINGER_PERIOD": str(settings.bollinger_period),
        "QX_BOLLINGER_DEVIATION": str(settings.bollinger_deviation),
    })
    return env


@app.post("/api/start")
async def start_bot(settings: StartSettings, authenticated: bool = Depends(verify_token)):
    global process, current_settings
    if not (ROOT / ".env").exists():
        raise HTTPException(400, detail="Missing .env with QX_EMAIL and QX_PASSWORD")
    if process and process.poll() is None:
        raise HTTPException(400, detail="Bot already running")

    if STOP_FILE.exists():
        STOP_FILE.unlink()

    env = build_env(settings)
    py = str(VENV_PY if VENV_PY.exists() else shutil.which("python"))
    if not py:
        raise HTTPException(500, detail="Python interpreter not found")

    try:
        process = subprocess.Popen(
            [py, str(STRATEGY)], cwd=str(ROOT), env=env,
            stdout=None, stderr=None,  # Let output go to main terminal
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if hasattr(subprocess, 'CREATE_NEW_PROCESS_GROUP') else 0,
        )
        current_settings = settings.dict()
        return {"ok": True}
    except Exception as exc:
        raise HTTPException(500, detail=f"Failed to start: {exc}")


@app.post("/api/stop")
async def stop_bot(authenticated: bool = Depends(verify_token)):
    global process
    STOP_FILE.write_text("stop")
    await asyncio.sleep(1.0)
    if process and process.poll() is None:
        try:
            if os.name == "nt":
                process.send_signal(signal.CTRL_BREAK_EVENT)
                await asyncio.sleep(2.0)
            process.terminate()
            await asyncio.sleep(1.0)
            if process.poll() is None:
                process.kill()
        except Exception:
            pass
    return {"ok": True}


@app.get("/api/status")
async def status():
    running = bool(process and process.poll() is None)
    
    # Get real-time balance if bot is running
    current_balance = 0
    if running:
        try:
            load_dotenv()
            email = os.getenv("QX_EMAIL")
            password = os.getenv("QX_PASSWORD")
            
            if email and password:
                client = Quotex(email=email, password=password, lang="en")
                connected, _ = await client.connect()
                if connected:
                    account_mode = current_settings.get("account", "PRACTICE")
                    await client.change_account(account_mode)
                    await asyncio.sleep(0.2)
                    current_balance = await client.get_balance()
                    await client.close()
        except:
            pass  # Ignore errors, use 0 balance
    
    return {
        "running": running,
        "settings": current_settings,
        "current_balance": current_balance
    }


@app.get("/api/refresh_assets")
async def refresh_assets(payout: float = 84):
    load_dotenv()
    email = os.getenv("QX_EMAIL")
    password = os.getenv("QX_PASSWORD")
    
    if not email or not password:
        raise HTTPException(400, "Missing credentials")
    
    try:
        print(f"🔄 Refreshing assets with payout threshold: {payout}%")
        client = Quotex(email=email, password=password, lang="en")
        connected, reason = await client.connect()
        
        if not connected:
            raise HTTPException(500, f"Connection failed: {reason}")
        
        all_assets = live_assets + otc_assets
        tradable_assets = await get_payout_filtered_assets(client, all_assets, payout)
        await client.close()
        
        return {"assets": tradable_assets}
        
    except Exception as e:
        print(f"❌ Error refreshing assets: {e}")
        raise HTTPException(500, str(e))


app.mount("/", StaticFiles(directory=str(ROOT / "frontend"), html=True), name="static")
