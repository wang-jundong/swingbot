"""GeckoTerminal public API: Solana pools and 5-minute OHLCV."""

from __future__ import annotations

import threading
import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.config.backtest import (
    GECKO_ACCEPT,
    GECKO_BASE_URL,
    GECKO_NETWORK,
    GECKO_OHLCV_LIMIT,
    GECKO_REQUEST_PAUSE_SEC,
    GECKO_REQUEST_RETRIES,
    GECKO_REQUEST_RETRY_BACKOFF_SEC,
    GECKO_TIMEOUT_SEC,
    GECKO_USER_AGENT,
)
from src.config.solana import SOL_ADDRESS
from src.utils.number_util import to_float

_RETRY_STATUSES = (429, 500, 502, 503, 504)
_LOCK = threading.Lock()
_NEXT_OK = 0.0


def _http_session() -> requests.Session:
    retry = Retry(
        total=GECKO_REQUEST_RETRIES,
        connect=GECKO_REQUEST_RETRIES,
        read=GECKO_REQUEST_RETRIES,
        backoff_factor=GECKO_REQUEST_RETRY_BACKOFF_SEC,
        status_forcelist=_RETRY_STATUSES,
        allowed_methods=("GET",),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


_THREAD = threading.local()


def _session() -> requests.Session:
    session = getattr(_THREAD, "session", None)
    if session is None:
        session = _http_session()
        _THREAD.session = session
    return session


def _throttle() -> None:
    global _NEXT_OK
    with _LOCK:
        now = time.monotonic()
        wait = _NEXT_OK - now
        if wait > 0:
            time.sleep(wait)
        _NEXT_OK = time.monotonic() + GECKO_REQUEST_PAUSE_SEC


def get(path: str, params: dict[str, Any] | None = None) -> Any:
    """GET /api/v2/{path} with rate limiting and retries."""
    url = f"{GECKO_BASE_URL.rstrip('/')}/{path.lstrip('/')}"
    last_error: Exception | None = None
    for attempt in range(GECKO_REQUEST_RETRIES):
        _throttle()
        try:
            response = _session().get(
                url,
                params=params or {},
                headers={
                    "Accept": GECKO_ACCEPT,
                    "User-Agent": GECKO_USER_AGENT,
                },
                timeout=GECKO_TIMEOUT_SEC,
            )
            if response.status_code == 429:
                last_error = RuntimeError("GeckoTerminal HTTP 429")
                time.sleep(GECKO_REQUEST_RETRY_BACKOFF_SEC * (attempt + 1) * 5)
                continue
            if response.status_code in _RETRY_STATUSES:
                last_error = RuntimeError(f"GeckoTerminal HTTP {response.status_code}")
                time.sleep(GECKO_REQUEST_RETRY_BACKOFF_SEC * (attempt + 1))
                continue
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            time.sleep(GECKO_REQUEST_RETRY_BACKOFF_SEC * (attempt + 1))
    raise RuntimeError(f"GeckoTerminal GET {path} failed: {last_error}")


def get_token_pools(mint: str, *, network: str = GECKO_NETWORK) -> list[dict]:
    payload = get(f"networks/{network}/tokens/{mint}/pools")
    rows = payload.get("data") if isinstance(payload, dict) else None
    return [row for row in (rows or []) if isinstance(row, dict)]


def get_pool_ohlcv(
    pool: str,
    *,
    timeframe: str = "minute",
    aggregate: int = 5,
    before_timestamp: int | None = None,
    limit: int = GECKO_OHLCV_LIMIT,
    currency: str = "token",
    token: str = "base",
    network: str = GECKO_NETWORK,
) -> list:
    params: dict[str, Any] = {
        "aggregate": aggregate,
        "limit": min(limit, GECKO_OHLCV_LIMIT),
        "currency": currency,
        "token": token,
    }
    if before_timestamp is not None:
        params["before_timestamp"] = int(before_timestamp)
    payload = get(f"networks/{network}/pools/{pool}/ohlcv/{timeframe}", params)
    attrs = ((payload or {}).get("data") or {}).get("attributes") or {}
    rows = attrs.get("ohlcv_list") or []
    return rows if isinstance(rows, list) else []


def token_address(ref: Any) -> str:
    """`solana_<mint>` relationship id or a raw address."""
    if isinstance(ref, dict):
        ref = ((ref.get("data") or {}).get("id") or ref.get("id") or "")
    text = str(ref or "")
    if "_" in text:
        return text.split("_", 1)[1]
    return text


def select_pool(pools: list[dict], mint: str, *, sol: str = SOL_ADDRESS) -> dict | None:
    """Prefer the highest-liquidity SOL pool that trades `mint`."""
    mint_l = mint.lower()
    sol_l = sol.lower()
    ranked: list[tuple[int, float, dict]] = []
    for pool in pools:
        attrs = pool.get("attributes") or {}
        rel = pool.get("relationships") or {}
        address = attrs.get("address")
        if not address:
            continue
        base = token_address(rel.get("base_token")).lower()
        quote = token_address(rel.get("quote_token")).lower()
        if mint_l not in (base, quote):
            continue
        sol_pair = int(sol_l in (base, quote))
        liquidity = to_float(attrs.get("reserve_in_usd")) or 0.0
        ranked.append((sol_pair, liquidity, pool))
    if not ranked:
        return None
    ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)
    return ranked[0][2]


def pool_meta(pool: dict, mint: str) -> dict:
    attrs = pool.get("attributes") or {}
    rel = pool.get("relationships") or {}
    base = token_address(rel.get("base_token"))
    quote = token_address(rel.get("quote_token"))
    mint_l = mint.lower()
    side = "base" if base.lower() == mint_l else "quote"
    return {
        "pool": attrs.get("address"),
        "pool_name": attrs.get("name"),
        "pool_created_at": attrs.get("pool_created_at"),
        "reserve_in_usd": to_float(attrs.get("reserve_in_usd")),
        "base": base,
        "quote": quote,
        "token_side": side,
        "market": attrs.get("address"),
        "dex": token_address((rel.get("dex") or {}).get("data")),
    }


def parse_ohlcv_list(rows: list) -> list[dict]:
    """Map GT `[t,o,h,l,c,v]` rows to candle dicts. Last duplicate timestamp wins."""
    candles: dict[int, dict] = {}
    for row in rows or []:
        if not isinstance(row, (list, tuple)) or len(row) < 6:
            continue
        unix = to_float(row[0])
        open_ = to_float(row[1])
        high = to_float(row[2])
        low = to_float(row[3])
        close = to_float(row[4])
        volume = to_float(row[5])
        if unix is None or close is None:
            continue
        stamp = int(unix)
        candles[stamp] = {
            "unix_time": stamp,
            "open": open_ if open_ is not None else close,
            "high": high if high is not None else close,
            "low": low if low is not None else close,
            "close": close,
            "volume_sol": volume or 0.0,
        }
    return [candles[key] for key in sorted(candles)]


def filter_window(
    candles: list[dict],
    time_from: int,
    time_to: int,
) -> list[dict]:
    start = int(time_from)
    end = int(time_to)
    return [
        candle
        for candle in candles
        if start <= int(candle.get("unix_time") or 0) <= end
    ]
