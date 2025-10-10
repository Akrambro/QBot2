# Quotex Trading Bot

This is a Python-based trading bot for the Quotex platform, featuring a web-based UI for control and monitoring. It uses the `pyquotex` library to interact with the Quotex API and a FastAPI backend to serve the frontend.

## Features

-   **Web Interface:** A modern web UI to start/stop the bot and configure all trading parameters.
-   **Dual Account Mode:** Supports both Practice and Real trading accounts.
-   **Live Balances:** Displays both your Real and Practice account balances in real-time.
-   **Dynamic Asset Filtering:** Automatically fetches all available assets and filters them based on your desired payout percentage.
-   **Active Trade Log:** Shows a live log of all trades that are currently in progress.
-   **Daily Trade History:** Provides a history of all trades executed on the current day, including PNL.
-   **Risk Management:** Allows you to set daily profit and loss limits (either as a percentage of your starting balance or as a fixed amount) to automatically stop the bot.

## Setup Instructions

### 1. Clone the Repository
Clone this repository to your local machine.

### 2. Create and Activate a Virtual Environment
It is highly recommended to use a virtual environment.

**On Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**On macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
Install the required Python packages.

```bash
pip install -r requirements.txt
```

### 4. Install Browser Dependencies
The bot uses Playwright to interact with the trading platform. You need to install its browser dependencies.

```bash
playwright install --with-deps
```

## Configuration

The bot is configured using environment variables.

1.  **Create a `.env` file:**
    Copy the example configuration file:
    ```bash
    copy .env.example .env
    ```
    (or `cp .env.example .env` on macOS/Linux)

2.  **Edit the `.env` file:**
    Open the `.env` file in a text editor and fill in your details.

    | Variable                  | Description                                                                 |
    | ------------------------- | --------------------------------------------------------------------------- |
    | `QX_EMAIL`                | Your Quotex account email.                                                  |
    | `QX_PASSWORD`             | Your Quotex account password.                                               |
    | `QX_PAYOUT`               | The minimum payout percentage for an asset to be considered tradable.       |
    | `QX_TIMEFRAME`            | The duration of each trade in seconds.                                      |
    | `QX_TRADE_PERCENT`        | The percentage of your balance to use for each trade.                       |
    | `QX_ACCOUNT`              | The default account to use (`PRACTICE` or `REAL`).                          |
    | `QX_DAILY_PROFIT`         | The daily profit target. Set to 0 to disable.                               |
    | `QX_DAILY_PROFIT_IS_PERCENT`| `1` if the profit target is a percentage, `0` if it is a fixed amount.       |
    | `QX_DAILY_LOSS`           | The daily loss limit. Set to 0 to disable.                                  |
    | `QX_DAILY_LOSS_IS_PERCENT`| `1` if the loss limit is a percentage, `0` if it is a fixed amount.          |


## Running the Application

To start the web server and the bot's user interface, run the `main.py` script:

```bash
python main.py
```

Once the server is running, open your web browser and navigate to:
[http://127.0.0.1:8000](http://127.0.0.1:8000)


# The port 8000 is already in use. Let me kill the existing process and start fresh:

## Kill any existing processes using port 8000
shell command: pkill -f "python main.py" || pkill -f "uvicorn" || fuser -k 8000/tcp || true

## Check what's using port 8000 and kill it
shell command: lsof -ti:8000 | xargs kill -9 2>/dev/null || true