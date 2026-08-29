"""Backtest cache paths, candle interval, and fetch windows."""

from pathlib import Path

from src.config.trading import HOLD_DAYS

CACHE_DIR = Path("var/backtest")
UNIVERSE_PATH = CACHE_DIR / "universe.json"
WALLET_FILLS_PATH = CACHE_DIR / "wallet_fills.json"
OHLCV_DIR = CACHE_DIR / "ohlcv"

CANDLE_INTERVAL_SEC = 5 * 60
LOOKBACK_SEC = 24 * 3600
HOLD_WINDOW_SEC = HOLD_DAYS * 86400

GECKO_BASE_URL = "https://api.geckoterminal.com/api/v2"
GECKO_NETWORK = "solana"
GECKO_ACCEPT = "application/json;version=20230302"
GECKO_USER_AGENT = "swingbot-backtest/1.0"
GECKO_OHLCV_LIMIT = 1000
GECKO_MAX_OHLCV_PAGES = 20
GECKO_TIMEOUT_SEC = 30
GECKO_REQUEST_PAUSE_SEC = 2.2
GECKO_REQUEST_RETRIES = 5
GECKO_REQUEST_RETRY_BACKOFF_SEC = 1.0

REQUEST_PAUSE_SEC = 0.12
REQUEST_RETRIES = 5
REQUEST_RETRY_BACKOFF_SEC = 1.0
TX_PAGE_LIMIT = 1000
MAX_PAGES_PER_MARKET = 600
