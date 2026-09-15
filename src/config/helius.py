"""Helius Enhanced Transactions API."""

HELIUS_TX_HISTORY_URL = (
    "https://api-mainnet.helius-rpc.com/v0/addresses/{address}/transactions"
)
PAGE_LIMIT = 100
REQUEST_PAUSE_SEC = 0.2
REQUEST_RETRIES = 3
REQUEST_RETRY_BACKOFF_SEC = 0.5
TOKEN_ACCOUNTS = "balanceChanged"
