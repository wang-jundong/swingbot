"""Helius RPC helpers for historical wallet transactions."""

from __future__ import annotations

import threading
import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.config.backtest import (
    REQUEST_RETRIES,
    REQUEST_RETRY_BACKOFF_SEC,
    TX_PAGE_LIMIT,
)
from src.config.bindings.binding import BINDINGS
from src.config.solana import RPC_REQUEST_TIMEOUT_SEC
from src.dex.solana.core.connection import get_rpc_url

_RETRY_STATUSES = (429, 500, 502, 503, 504)


def _http_session() -> requests.Session:
    retry = Retry(
        total=REQUEST_RETRIES,
        connect=REQUEST_RETRIES,
        read=REQUEST_RETRIES,
        backoff_factor=REQUEST_RETRY_BACKOFF_SEC,
        status_forcelist=_RETRY_STATUSES,
        allowed_methods=("POST",),
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


def rpc_url() -> str:
    return get_rpc_url() or BINDINGS["SOLANA_RPC_URL"].strip()


def rpc(method: str, params: Any, *, url: str | None = None) -> Any:
    """JSON-RPC call with retries. `params` may be a list or object."""
    endpoint = url or rpc_url()
    last_error: Exception | None = None
    for attempt in range(REQUEST_RETRIES):
        try:
            response = _session().post(
                endpoint,
                json={
                    "jsonrpc": "2.0",
                    "id": method,
                    "method": method,
                    "params": params,
                },
                timeout=RPC_REQUEST_TIMEOUT_SEC,
            )
            if response.status_code in _RETRY_STATUSES:
                raise RuntimeError(f"RPC HTTP {response.status_code}")
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError, RuntimeError) as exc:
            last_error = exc
            time.sleep(REQUEST_RETRY_BACKOFF_SEC * (attempt + 1))
            continue

        if payload.get("error"):
            message = payload["error"].get("message", payload["error"])
            text = str(message).lower()
            if "rate limit" in text or "429" in text:
                last_error = RuntimeError(f"RPC {method} error: {message}")
                time.sleep(REQUEST_RETRY_BACKOFF_SEC * (attempt + 1))
                continue
            raise RuntimeError(f"RPC {method} error: {message}")
        if "result" not in payload:
            raise RuntimeError(f"RPC {method} response missing result")
        return payload["result"]

    raise RuntimeError(f"RPC {method} failed after retries: {last_error}")


def get_transactions_page(
    address: str,
    *,
    time_from: int,
    time_to: int,
    limit: int = TX_PAGE_LIMIT,
    details: str = "full",
    pagination_token: str | None = None,
    extra_filters: dict[str, Any] | None = None,
    url: str | None = None,
) -> tuple[list[dict], str | None]:
    """One page of getTransactionsForAddress. Returns (rows, pagination_token)."""
    filters: dict[str, Any] = {
        "status": "succeeded",
        "blockTime": {"gte": int(time_from), "lte": int(time_to)},
    }
    if extra_filters:
        filters.update(extra_filters)
    config: dict[str, Any] = {
        "transactionDetails": details,
        "sortOrder": "asc",
        "limit": limit,
        "maxSupportedTransactionVersion": 0,
        "filters": filters,
    }
    if details == "full":
        config["encoding"] = "jsonParsed"
    if pagination_token:
        config["paginationToken"] = pagination_token
    result = rpc("getTransactionsForAddress", [address, config], url=url) or {}
    if not isinstance(result, dict):
        return [], None
    return list(result.get("data") or []), result.get("paginationToken")
