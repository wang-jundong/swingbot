"""Birdeye token screener and OHLCV export."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.config.bindings.binding import BINDINGS
from src.config.bindings.paths import BIRDEYE_PATH, WALLET_TRADES_PATH
from src.config.birdeye import (
    BIRDEYE_OHLCV_URL,
    BIRDEYE_PRICE_STATS_URL,
    BIRDEYE_TOKEN_LIST_URL,
    LIQUIDITY_USD_MIN,
    MAX_PAGES,
    OHLC_CURRENCY,
    OHLC_INTERVAL,
    OHLC_INTERVAL_SEC,
    OHLC_MAX_CANDLES,
    PAGE_LIMIT,
    PAIR_AGE_DAYS_MAX,
    PAIR_AGE_DAYS_MIN,
    PRICE_CHANGE_DROP_PCT,
    PRICE_RANGE_MAX_PCT,
    PUMP_FUN_MINT_SUFFIX,
    REQUEST_PAUSE_SEC,
    TXNS_H24_MIN,
    VOLUME_1H_CHANGE_PCT_MIN,
    VOLUME_24H_USD_MIN,
)
from src.config.track import LOOKBACK_HOURS
from src.dex.solana.jupiter.markets import fetch_sol_usd, price_sol
from src.storage.ohlc import load_ohlc_file, wallet_ohlc_folder, write_ohlc_file
from src.utils.log_util import get_dex_logger
from src.utils.number_util import to_float
from src.utils.time_util import unix_now

SECONDS_PER_DAY = 86400
REQUEST_TIMEOUT_SEC = 30
REQUEST_RETRIES = 3
REQUEST_RETRY_BACKOFF_SEC = 0.5

logger = get_dex_logger()


def _http_session() -> requests.Session:
    retry = Retry(
        total=REQUEST_RETRIES,
        connect=REQUEST_RETRIES,
        read=REQUEST_RETRIES,
        backoff_factor=REQUEST_RETRY_BACKOFF_SEC,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


_SESSION = _http_session()


def api_key() -> str:
    path = Path(BIRDEYE_PATH)
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        data = {}
    if isinstance(data, dict):
        key = str(data.get("api_key") or "").strip()
        if key:
            return key
    return BINDINGS["BIRDEYE_API_KEY"].strip()


def headers() -> dict:
    return {
        "X-API-KEY": api_key(),
        "x-chain": "solana",
        "accept": "application/json",
    }


def export_wallet_ohlc(
    wallet: str,
    *,
    lookback_hours: float | None = None,
    interval: str | None = None,
) -> tuple[Path, list[dict]]:
    """Fetch Birdeye OHLCV for every scanned mint and write var/ohlc/<wallet>."""
    owner = str(wallet or "").strip()
    mints = load_wallet_trade_mints(owner)
    folder = wallet_ohlc_folder(owner)
    rows = []
    fetched = False
    for token in mints:
        if fetched:
            time.sleep(REQUEST_PAUSE_SEC)
            fetched = False
        try:
            row = export_mint_ohlc(
                owner,
                token["mint"],
                lookback_hours=lookback_hours,
                interval=interval,
            )
            fetched = bool(row.get("fetched"))
            rows.append(row)
        except Exception:
            logger.exception("birdeye ohlcv failed mint=%s", token.get("mint"))
            rows.append({**token, "candles": 0, "error": True, "resumed": False})
    return folder, rows


def export_mint_ohlc(
    wallet: str,
    mint: str,
    *,
    lookback_hours: float | None = None,
    interval: str | None = None,
) -> dict:
    """Resume Birdeye OHLCV for one mint and write var/ohlc/<wallet>/<mint>.json."""
    owner = str(wallet or "").strip()
    token_id = str(mint or "").strip()
    if not owner or not token_id:
        raise ValueError("wallet and mint are required")
    key = interval if interval in OHLC_INTERVAL_SEC else OHLC_INTERVAL
    token = load_wallet_trade_mint(owner, token_id) or {"mint": token_id}
    existing = load_ohlc_file(owner, token_id)
    if existing:
        token["name"] = token.get("name") or str(existing.get("name") or "").strip()
        token["symbol"] = token.get("symbol") or str(existing.get("symbol") or "").strip()
        if not token.get("creation_time"):
            token["creation_time"] = _int_or_none(existing.get("creation_time"))
    window_from, time_to = _ohlc_window(token.get("first_ts"), lookback_hours)
    saved = _saved_candles(existing, key)
    time_from = saved[-1]["t"] if saved else window_from
    extra = []
    fetched = False
    if time_from < time_to:
        extra = fetch_ohlcv(token_id, time_from, time_to, interval=key)
        fetched = True
    candles = _merge_candles(saved, extra)
    now = unix_now()
    first_t = candles[0]["t"] if candles else time_from
    last_t = candles[-1]["t"] if candles else time_to
    created = token.get("creation_time") or first_t
    payload = {
        "mint": token_id,
        "name": token.get("name") or "",
        "symbol": token.get("symbol") or "",
        "source": "birdeye",
        "interval": key,
        "creation_time": created,
        "age_seconds": max(0, now - created),
        "time_from": first_t,
        "time_to": last_t,
        "candle_count": len(candles),
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "candles": candles,
    }
    if extra or not saved:
        write_ohlc_file(owner, payload)
    row = {
        **token,
        "mint": token_id,
        "wallet": owner,
        "candles": len(candles),
        "added": len(extra),
        "fetched": fetched,
        "resumed": bool(saved),
        "time_from": first_t,
        "time_to": last_t,
        "error": False,
    }
    logger.info(
        "birdeye ohlcv wallet=%s mint=%s candles=%d added=%d resumed=%s",
        owner, token_id, len(candles), len(extra), bool(saved),
    )
    return row


def load_wallet_trade_mints(wallet: str) -> list[dict]:
    folder = Path(WALLET_TRADES_PATH) / wallet
    if not folder.is_dir():
        raise RuntimeError(f"no trades for {wallet}; run python -m cli.scan_wallet first")
    rows = []
    for path in sorted(folder.glob("*.json")):
        row = _trade_file_row(path)
        if row:
            rows.append(row)
    if not rows:
        raise RuntimeError(f"no mint files in {folder}")
    return rows


def load_wallet_trade_mint(wallet: str, mint: str) -> dict | None:
    folder = Path(WALLET_TRADES_PATH) / wallet
    path = folder / f"{mint}.json"
    if not path.is_file():
        return None
    return _trade_file_row(path)


def _trade_file_row(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    mint = str(data.get("mint") or path.stem).strip()
    if not mint:
        return None
    stamps = [
        int(trade.get("timestamp") or 0)
        for trade in data.get("trades") or []
        if isinstance(trade, dict) and trade.get("timestamp")
    ]
    return {
        "mint": mint,
        "name": str(data.get("name") or "").strip(),
        "symbol": str(data.get("symbol") or "").strip(),
        "creation_time": _int_or_none(
            data.get("creation_time") if data.get("creation_time") is not None
            else data.get("created_time")
        ),
        "first_ts": min(stamps) if stamps else None,
        "last_ts": max(stamps) if stamps else None,
    }


def _int_or_none(value: object) -> int | None:
    number = to_float(value)
    return int(number) if number is not None else None


def fetch_ohlcv(
    address: str,
    time_from: int,
    time_to: int,
    *,
    interval: str | None = None,
) -> list[dict]:
    """Page Birdeye OHLCV v3 for one mint over [time_from, time_to]."""
    key = interval if interval in OHLC_INTERVAL_SEC else OHLC_INTERVAL
    step = OHLC_INTERVAL_SEC[key]
    start = int(time_from)
    end = int(time_to)
    if end <= start:
        return []
    candles: dict[int, dict] = {}
    cursor = start
    pages = 0
    while cursor < end:
        page_to = min(end, cursor + OHLC_MAX_CANDLES * step)
        if pages:
            time.sleep(REQUEST_PAUSE_SEC)
        items = _ohlcv_page(address, cursor, page_to, key)
        pages += 1
        for item in items:
            row = _normalize_candle(item)
            if row is None:
                continue
            candles[row["t"]] = row
        cursor = page_to
    return [candles[ts] for ts in sorted(candles)]


def _saved_candles(payload: dict | None, interval: str) -> list[dict]:
    if not isinstance(payload, dict):
        return []
    if str(payload.get("interval") or "") not in ("", interval):
        return []
    candles = []
    for item in payload.get("candles") or []:
        row = _normalize_candle({
            **item,
            "unix_time": item.get("unix_time") or item.get("t"),
        })
        if row:
            candles.append(row)
    candles.sort(key=lambda row: row["t"])
    return candles


def _merge_candles(old: list[dict], extra: list[dict]) -> list[dict]:
    by_t = {row["t"]: row for row in old}
    for row in extra:
        by_t[row["t"]] = row
    return [by_t[ts] for ts in sorted(by_t)]


def _ohlc_window(first_ts: int | None, lookback_hours: float | None) -> tuple[int, int]:
    now = unix_now()
    start = now
    if first_ts:
        start = min(start, int(first_ts))
    hours = LOOKBACK_HOURS if lookback_hours is None else lookback_hours
    if hours and hours > 0:
        start = min(start, now - int(float(hours) * 3600))
    if start >= now:
        start = now - SECONDS_PER_DAY
    step = OHLC_INTERVAL_SEC[OHLC_INTERVAL]
    start -= start % step
    return max(0, start), now


def _ohlcv_page(address: str, time_from: int, time_to: int, interval: str) -> list[dict]:
    response = _SESSION.get(
        BIRDEYE_OHLCV_URL,
        headers=headers(),
        params={
            "address": address,
            "type": interval,
            "currency": OHLC_CURRENCY,
            "mode": "range",
            "time_from": int(time_from),
            "time_to": int(time_to),
        },
        timeout=REQUEST_TIMEOUT_SEC,
    )
    response.raise_for_status()
    payload = response.json()
    data = payload.get("data") if isinstance(payload, dict) else None
    items = (data or {}).get("items") if isinstance(data, dict) else None
    return items if isinstance(items, list) else []


def _normalize_candle(item: dict) -> dict | None:
    if not isinstance(item, dict):
        return None
    t = to_float(item.get("unix_time") or item.get("unixTime"))
    close = to_float(item.get("c"))
    if t is None or close is None:
        return None
    high = to_float(item.get("h"))
    low = to_float(item.get("l"))
    return {
        "t": int(t),
        "o": to_float(item.get("o")) if to_float(item.get("o")) is not None else close,
        "h": high if high is not None else close,
        "l": low if low is not None else close,
        "c": close,
        "v": to_float(item.get("v")) or 0.0,
        "v_usd": to_float(item.get("v_usd") or item.get("vUsd")) or 0.0,
    }


def scan_tokens() -> list[dict]:
    matched = []
    for token in fetch_token_list():
        if not is_pump_fun_token(token):
            continue
        if not volume_filters(token):
            continue
        if not price_range_filters(token) or not price_change_filters(token):
            continue
        token["filter_reason"] = describe_filter_match(token)
        matched.append(token)
    _prices_to_sol(matched)
    return matched


def _prices_to_sol(tokens: list[dict]) -> None:
    if not tokens:
        return
    sol_usd = fetch_sol_usd()
    for token in tokens:
        token["price"] = price_sol(token.get("price"), sol_usd)


def is_pump_fun_token(token: dict) -> bool:
    address = token.get("address") or ""
    return str(address).endswith(PUMP_FUN_MINT_SUFFIX)


def volume_filters(token: dict) -> bool:
    volume = token.get("volume_24h_usd")
    if volume is None or volume <= VOLUME_24H_USD_MIN:
        return False
    return volume_reason(token) is not None


def fetch_token_list() -> list[dict]:
    now = int(time.time())
    params = {
        "sort_by": "trade_24h_count",
        "sort_type": "desc",
        "limit": PAGE_LIMIT,
        "min_liquidity": LIQUIDITY_USD_MIN,
        "min_recent_listing_time": now - PAIR_AGE_DAYS_MAX * SECONDS_PER_DAY,
        "max_recent_listing_time": now - PAIR_AGE_DAYS_MIN * SECONDS_PER_DAY,
        "min_trade_24h_count": TXNS_H24_MIN,
    }

    tokens = []
    for page in range(MAX_PAGES):
        params["offset"] = page * PAGE_LIMIT
        try:
            response = _SESSION.get(
                BIRDEYE_TOKEN_LIST_URL,
                headers=headers(),
                params=params,
                timeout=REQUEST_TIMEOUT_SEC,
            )
            response.raise_for_status()
            data = response.json().get("data") or {}
        except (requests.RequestException, ValueError):
            logger.exception("birdeye token list page %d failed", page)
            break

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
        response = _SESSION.get(
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
    if pass_all_down(token):
        return False
    return pass_reason(token) is not None


def pass_all_down(token: dict) -> bool:
    changes = [
        token.get("price_change_1h_percent"),
        token.get("price_change_2h_percent"),
        token.get("price_change_4h_percent"),
        token.get("price_change_8h_percent"),
    ]
    return all(c is not None and c < 0 for c in changes) and any(
        c < PRICE_CHANGE_DROP_PCT for c in changes
    )


def pass_reason(token: dict) -> str | None:
    return pass_1h(token) or pass_vs_1h_high(token)


def pass_1h(token: dict) -> str | None:
    change_1h = token.get("price_change_1h_percent")
    if change_1h is not None and change_1h < PRICE_CHANGE_DROP_PCT:
        return f"pass_1h={change_1h:.1f}%"
    return None


def pass_vs_1h_high(token: dict) -> str | None:
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


def volume_reason(token: dict) -> str | None:
    change_1h = token.get("volume_1h_change_percent")
    if change_1h is not None and change_1h > VOLUME_1H_CHANGE_PCT_MIN:
        return f"vol_1h_chg={change_1h:.1f}%"

    vol_1h = token.get("volume_1h_usd")
    vol_24h = token.get("volume_24h_usd")
    if (
        vol_1h is not None
        and vol_24h is not None
        and vol_24h > 0
        and vol_1h * 24 > vol_24h
    ):
        return f"vol_1h_hot={vol_1h:.0f}*24>{vol_24h:.0f}"
    return None


def describe_filter_match(token: dict) -> str:
    parts = [
        part
        for part in (volume_reason(token), range_reason(token), pass_reason(token))
        if part
    ]
    return ", ".join(parts)


def normalize_token(item: dict, now: int) -> dict:
    listed_at = item.get("recent_listing_time")
    age_days = (now - listed_at) / SECONDS_PER_DAY if listed_at else None
    return {
        "name": item.get("name"),
        "symbol": item.get("symbol"),
        "address": item.get("address"),
        "liquidity_usd": item.get("liquidity"),
        "volume_1h_usd": item.get("volume_1h_usd"),
        "volume_1h_change_percent": item.get("volume_1h_change_percent"),
        "volume_24h_usd": item.get("volume_24h_usd"),
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
