"""Birdeye Data API endpoints and token-scan filters."""

BIRDEYE_TOKEN_LIST_URL = "https://public-api.birdeye.so/defi/v3/token/list"
BIRDEYE_PRICE_STATS_URL = "https://public-api.birdeye.so/defi/v3/price/stats/single"

LIQUIDITY_USD_MIN = 10_000
VOLUME_24H_USD_MIN = 50_000
VOLUME_1H_CHANGE_PCT_MIN = 0
PAIR_AGE_DAYS_MIN = 1
PAIR_AGE_DAYS_MAX = 10
TXNS_H24_MIN = 1_000
PUMP_FUN_MINT_SUFFIX = "pump"

PRICE_RANGE_MAX_PCT = {
    "24h": 50,
    "8h": 30,
}
PRICE_CHANGE_DROP_PCT = -10

PAGE_LIMIT = 100
MAX_PAGES = 100
REQUEST_PAUSE_SEC = 0.35
