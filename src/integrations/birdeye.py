"""Birdeye token screener (Token List V3)."""

import time

import requests

from src.config.bindings.binding import BINDINGS
from src.config.birdeye import (
    BIRDEYE_PRICE_STATS_URL,
    BIRDEYE_TOKEN_LIST_URL,
    LIQUIDITY_USD_MAX,
    LIQUIDITY_USD_MIN,
    MAX_PAGES,
    PAGE_LIMIT,
    PAIR_AGE_DAYS_MAX,
    PAIR_AGE_DAYS_MIN,
    PRICE_CHANGE_DROP_PCT,
    PRICE_RANGE_MAX_PCT,
    REQUEST_PAUSE_SEC,
    TXNS_H24_MIN,
)

SECONDS_PER_DAY = 86400
REQUEST_TIMEOUT_SEC = 30


def headers() -> dict:
    return {
        "X-API-KEY": BINDINGS["BIRDEYE_API_KEY"].strip(),
        "x-chain": "solana",
        "accept": "application/json",
    }


def scan_tokens() -> list[dict]:
    matched = []
    for token in fetch_token_list():
        if not price_range_filters(token) or not price_change_filters(token):
            continue
        token["filter_reason"] = describe_filter_match(token)
        matched.append(token)
    return matched


def fetch_token_list() -> list[dict]:
    now = int(time.time())
    params = {
        "sort_by": "trade_24h_count",
        "sort_type": "desc",
        "limit": PAGE_LIMIT,
        "min_liquidity": LIQUIDITY_USD_MIN,
        "max_liquidity": LIQUIDITY_USD_MAX,
        "min_recent_listing_time": now - PAIR_AGE_DAYS_MAX * SECONDS_PER_DAY,
        "max_recent_listing_time": now - PAIR_AGE_DAYS_MIN * SECONDS_PER_DAY,
        "min_trade_24h_count": TXNS_H24_MIN,
    }

    tokens = []
    for page in range(MAX_PAGES):
        params["offset"] = page * PAGE_LIMIT
        response = requests.get(
            BIRDEYE_TOKEN_LIST_URL,
            headers=headers(),
            params=params,
            timeout=REQUEST_TIMEOUT_SEC,
        )
        response.raise_for_status()

        data = response.json().get("data") or {}
        items = data.get("items") or []
        if not items:
            break

        tokens.extend(normalize_token(item, now) for item in items)
        if not data.get("hasNext"):
            break
        time.sleep(REQUEST_PAUSE_SEC)
    return tokens


def fetch_price_stats(
    address: str, timeframes: list[str],
) -> dict[str, dict] | None:
    try:
        response = requests.get(
            BIRDEYE_PRICE_STATS_URL,
            headers=headers(),
            params={"address": address, "list_timeframe": ",".join(timeframes)},
            timeout=REQUEST_TIMEOUT_SEC,
        )
        response.raise_for_status()
        items = response.json().get("data") or []
    except (requests.RequestException, ValueError):
        return None

    frames = (items[0].get("data") or []) if items else []
    return {frame["time_frame"]: frame for frame in frames if frame.get("time_frame")}


def price_range_filters(token: dict) -> bool:
    address = token.get("address")
    if not address:
        return False

    time.sleep(REQUEST_PAUSE_SEC)
    stats_by_timeframe = fetch_price_stats(
        address, [*PRICE_RANGE_MAX_PCT, "1h"],
    )
    if stats_by_timeframe is None:
        return False

    range_pct_by_timeframe = {}
    for timeframe in PRICE_RANGE_MAX_PCT:
        range_pct = range_percent(stats_by_timeframe.get(timeframe))
        if range_pct is None:
            return False
        range_pct_by_timeframe[timeframe] = range_pct

    matched = any(
        range_pct_by_timeframe[timeframe] < max_pct
        for timeframe, max_pct in PRICE_RANGE_MAX_PCT.items()
    )
    if not matched:
        return False

    for timeframe, range_pct in range_pct_by_timeframe.items():
        token[f"price_range_{timeframe}_pct"] = range_pct

    high_1h = (stats_by_timeframe.get("1h") or {}).get("high")
    price = token.get("price")
    if high_1h is not None and high_1h > 0 and price is not None:
        token["price_vs_1h_high_pct"] = (price - high_1h) / high_1h * 100
    return True


def price_change_filters(token: dict) -> bool:
    return pass_reason(token) is not None


def pass_reason(token: dict) -> str | None:
    change_1h = token.get("price_change_1h_percent")
    change_2h = token.get("price_change_2h_percent")
    change_4h = token.get("price_change_4h_percent")
    change_8h = token.get("price_change_8h_percent")
    changes = [change_1h, change_2h, change_4h, change_8h]

    if change_1h is not None and change_1h < PRICE_CHANGE_DROP_PCT:
        return f"pass_1h={change_1h:.1f}%"

    if all(c is not None and c < 0 for c in changes) and any(
        c < PRICE_CHANGE_DROP_PCT for c in changes
    ):
        labels = ("1h", "2h", "4h", "8h")
        passed = ", ".join(
            f"{label}={change:.1f}%"
            for label, change in zip(labels, changes)
            if change < PRICE_CHANGE_DROP_PCT
        )
        return f"pass_all_down({passed})"

    vs_high_pct = token.get("price_vs_1h_high_pct")
    if vs_high_pct is not None and vs_high_pct < PRICE_CHANGE_DROP_PCT:
        return f"pass_vs_1h_high={vs_high_pct:.1f}%"
    return None


def range_reason(token: dict) -> str:
    parts = []
    for timeframe, max_pct in PRICE_RANGE_MAX_PCT.items():
        range_pct = token.get(f"price_range_{timeframe}_pct")
        if range_pct is not None and range_pct < max_pct:
            parts.append(f"range_{timeframe}={range_pct:.1f}%")
    return ", ".join(parts)


def describe_filter_match(token: dict) -> str:
    parts = [part for part in (range_reason(token), pass_reason(token)) if part]
    return ", ".join(parts)


def normalize_token(item: dict, now: int) -> dict:
    listed_at = item.get("recent_listing_time")
    age_days = (now - listed_at) / SECONDS_PER_DAY if listed_at else None
    return {
        "name": item.get("name"),
        "symbol": item.get("symbol"),
        "address": item.get("address"),
        "liquidity_usd": item.get("liquidity"),
        "pair_age_days": age_days,
        "holders": item.get("holder"),
        "txns_h24": item.get("trade_24h_count"),
        "price": item.get("price"),
        "price_change_1h_percent": item.get("price_change_1h_percent"),
        "price_change_2h_percent": item.get("price_change_2h_percent"),
        "price_change_4h_percent": item.get("price_change_4h_percent"),
        "price_change_8h_percent": item.get("price_change_8h_percent"),
    }


def range_percent(stats: dict | None) -> float | None:
    if not stats:
        return None
    high = stats.get("high")
    low = stats.get("low")
    if high is None or low is None or high <= 0:
        return None
    return (high - low) / high * 100
