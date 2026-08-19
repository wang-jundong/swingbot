"""Jupiter Tokens API v2 market stats."""

from __future__ import annotations

from datetime import datetime, timezone

import requests

from src.config.bindings.binding import BINDINGS
from src.config.solana import RPC_REQUEST_TIMEOUT_SEC, SOL_ADDRESS
from src.utils.number_util import to_float
from src.utils.time_util import unix_now
from src.utils.log_util import get_dex_logger

logger = get_dex_logger()

SEARCH_PATH = "/tokens/v2/search"
CHUNK_SIZE = 100
SECONDS_PER_DAY = 86400


def fetch_token_markets(addresses: list[str]) -> dict[str, dict]:
    """Liquidity in SOL, pair age, 24h volume, and 24h txns keyed by mint."""
    unique = [address for address in dict.fromkeys(addresses) if address]
    query = list(unique)
    if SOL_ADDRESS not in query:
        query.append(SOL_ADDRESS)
    markets: dict[str, dict] = {}
    for offset in range(0, len(query), CHUNK_SIZE):
        chunk = query[offset:offset + CHUNK_SIZE]
        try:
            rows = _search(chunk)
        except Exception:
            logger.exception("Jupiter token search failed")
            continue
        for row in rows:
            mint = str(row.get("id") or "")
            if mint:
                markets[mint] = _market(row)
    sol_usd = (markets.get(SOL_ADDRESS) or {}).get("usd_price")
    for mint, stats in markets.items():
        stats["liquidity"] = _liquidity_sol(stats.get("liquidity_usd"), sol_usd)
        stats["price"] = _price_sol(stats.get("usd_price"), sol_usd)
    return {mint: stats for mint, stats in markets.items() if mint != SOL_ADDRESS}


def _search(mints: list[str]) -> list[dict]:
    url = f"{BINDINGS['JUPITER_BASE_URL'].strip().rstrip('/')}{SEARCH_PATH}"
    headers = {"x-api-key": BINDINGS["JUPITER_API_KEY"].strip()}
    response = requests.get(
        url,
        params={"query": ",".join(mints)},
        headers=headers,
        timeout=RPC_REQUEST_TIMEOUT_SEC,
    )
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, list) else []


def _market(row: dict) -> dict:
    stats = row.get("stats24h") or {}
    buys = to_float(stats.get("numBuys")) or 0.0
    sells = to_float(stats.get("numSells")) or 0.0
    return {
        "liquidity_usd": to_float(row.get("liquidity")),
        "usd_price": to_float(row.get("usdPrice")),
        "pair_age": _pair_age_days(row),
        "volume_24h": _window_volume(row.get("stats24h")),
        "txns_24h": int(buys + sells) if stats else None,
    }


def _window_volume(stats: dict | None) -> float | None:
    if not stats:
        return None
    buy_vol = to_float(stats.get("buyVolume")) or 0.0
    sell_vol = to_float(stats.get("sellVolume")) or 0.0
    return round(buy_vol + sell_vol, 2)


def _liquidity_sol(liquidity_usd: float | None, sol_usd: float | None) -> float | None:
    if liquidity_usd is None or sol_usd is None or sol_usd <= 0:
        return None
    return round(liquidity_usd / sol_usd, 4)


def _price_sol(usd_price: float | None, sol_usd: float | None) -> float | None:
    if usd_price is None or sol_usd is None or sol_usd <= 0:
        return None
    return usd_price / sol_usd


def _pair_age_days(row: dict) -> float | None:
    pool = row.get("firstPool") or {}
    created = pool.get("createdAt") or row.get("createdAt")
    if not created:
        return None
    try:
        started = datetime.fromisoformat(str(created).replace("Z", "+00:00"))
    except ValueError:
        return None
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    age = (unix_now() - int(started.timestamp())) / SECONDS_PER_DAY
    return round(age, 2) if age >= 0 else None
