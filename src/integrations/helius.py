"""Helius wallet buy/sell scanner (Enhanced Transactions)."""

from __future__ import annotations

import json
import math
import re
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.config.bindings.binding import BINDINGS
from src.config.bindings.paths import WALLET_TRADES_PATH
from src.config.helius import (
    HELIUS_TX_HISTORY_URL,
    PAGE_LIMIT,
    REQUEST_PAUSE_SEC,
    REQUEST_RETRIES,
    REQUEST_RETRY_BACKOFF_SEC,
    TOKEN_ACCOUNTS,
)
from src.config.solana import (
    HELIUS_TIP_ACCOUNT,
    LAMPORTS_PER_SOL,
    RPC_REQUEST_TIMEOUT_SEC,
    SOL_ADDRESS,
)
from src.config.track import LOOKBACK_HOURS, MAX_TOKEN_AGE_DAYS, TARGET_WALLET
from src.dex.solana.jupiter.markets import fetch_token_metadata
from src.utils.log_util import get_dex_logger
from src.utils.number_util import to_float
from src.utils.time_util import unix_now

logger = get_dex_logger()

_CONTINUE_SIG = re.compile(r"parameter set to ([1-9A-HJ-NP-Za-km-z]+)")
_NFT_STANDARDS = {"NonFungible", "NonFungibleEdition", "ProgrammableNonFungible"}
_DESC_BUY = re.compile(r"(?i)swapped\s+[0-9.]+\s+SOL\s+for\s+[0-9.]+\s+(\S+)")
_DESC_SELL = re.compile(r"(?i)swapped\s+[0-9.]+\s+(\S+)\s+for\s+[0-9.]+\s+SOL")


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
    url = BINDINGS["SOLANA_RPC_URL"].strip()
    key = (parse_qs(urlparse(url).query).get("api-key") or [""])[0].strip()
    if not key:
        raise RuntimeError("SOLANA_RPC_URL is missing api-key")
    return key


def scan_wallet_trades(
    wallet: str | None = None,
    *,
    lookback_hours: float | None = None,
) -> tuple[list[dict], dict]:
    """Fetch Helius-parsed txs for the wallet and keep SOL buy/sell swaps.

    Existing mint files are kept; paging starts at the last saved trade.
    Returned trades exclude tokens older than MAX_TOKEN_AGE_DAYS at scan time.
    """
    owner = wallet or TARGET_WALLET
    saved, saved_meta = load_wallet_scan(owner)
    saved_keys = {_trade_key(trade) for trade in saved}
    window_from = _lookback_start(lookback_hours)
    last_ts = max((int(trade.get("timestamp") or 0) for trade in saved), default=0)
    time_from = last_ts if last_ts else window_from
    extra = []
    seen = set()
    for tx in fetch_wallet_transactions(owner, time_from=time_from):
        signature = str(tx.get("signature") or "")
        if not signature or signature in seen:
            continue
        seen.add(signature)
        for trade in parse_trades(tx, owner):
            if time_from and int(trade.get("timestamp") or 0) < time_from:
                continue
            extra.append(trade)
    trades = _merge_trades(saved, extra)
    meta = token_metadata(list(group_trades(trades)), trades, existing=saved_meta)
    trades, skipped_mints, unknown_age_mints = filter_token_age(trades, meta)
    added = sum(1 for trade in trades if _trade_key(trade) not in saved_keys)
    logger.info(
        "helius %s trades=%d added=%d txs=%d resumed=%s lookback=%s",
        owner,
        len(trades),
        added,
        len(seen),
        bool(saved),
        lookback_hours if lookback_hours is not None else LOOKBACK_HOURS,
    )
    return trades, {
        "resumed": bool(saved),
        "added": added,
        "meta": meta,
        "skipped_old_mints": len(skipped_mints),
        "unknown_age_mints": len(unknown_age_mints),
    }



def filter_token_age(
    trades: list[dict],
    meta: dict[str, dict],
    *,
    max_age_days: float = MAX_TOKEN_AGE_DAYS,
    now: int | None = None,
) -> tuple[list[dict], set[str], set[str]]:
    """Exclude known old mints; keep unknown ages and report them separately."""
    if not math.isfinite(max_age_days) or max_age_days < 0:
        raise ValueError("max_age_days must be finite and non-negative")
    if max_age_days == 0:
        return trades, set(), set()
    current = unix_now() if now is None else now
    cutoff = current - max_age_days * 86400
    skipped, unknown = set(), set()
    for mint in {str(trade.get("mint") or "") for trade in trades}:
        created = to_float((meta.get(mint) or {}).get("creation_time"))
        if created is None or not math.isfinite(created) or created <= 0 or created > current:
            unknown.add(mint)
        elif created < cutoff:
            skipped.add(mint)
    return [trade for trade in trades if trade.get("mint") not in skipped], skipped, unknown


def aggregate_trades(trades: list[dict]) -> list[dict]:
    """Roll buy/sell swaps up to one row per mint."""
    grouped: dict[str, dict] = {}
    for trade in trades:
        mint = str(trade.get("mint") or "")
        if not mint:
            continue
        row = grouped.get(mint)
        if row is None:
            row = {
                "mint": mint,
                "buy_count": 0,
                "sell_count": 0,
                "buy_sol": 0.0,
                "sell_sol": 0.0,
                "buy_token": 0.0,
                "sell_token": 0.0,
                "first_ts": None,
                "last_ts": None,
                "sources": [],
                "last_signature": "",
            }
            grouped[mint] = row
        action = str(trade.get("action") or "")
        sol_amount = to_float(trade.get("sol_amount")) or 0.0
        token_amount = to_float(trade.get("token_amount")) or 0.0
        if action == "buy":
            row["buy_count"] += 1
            row["buy_sol"] += sol_amount
            row["buy_token"] += token_amount
        elif action == "sell":
            row["sell_count"] += 1
            row["sell_sol"] += sol_amount
            row["sell_token"] += token_amount
        ts = int(trade.get("timestamp") or 0)
        if ts and (row["first_ts"] is None or ts < row["first_ts"]):
            row["first_ts"] = ts
        if ts and (row["last_ts"] is None or ts >= row["last_ts"]):
            row["last_ts"] = ts
            row["last_signature"] = str(trade.get("signature") or "")
        source = str(trade.get("source") or "")
        if source and source not in row["sources"]:
            row["sources"].append(source)

    rows = []
    for row in grouped.values():
        buy_token = row["buy_token"]
        sell_token = row["sell_token"]
        buy_sol = row["buy_sol"]
        sell_sol = row["sell_sol"]
        row["pnl_sol"] = sell_sol - buy_sol
        row["leftover"] = buy_token - sell_token
        row["buy_price"] = buy_sol / buy_token if buy_token else None
        row["sell_price"] = sell_sol / sell_token if sell_token else None
        rows.append(row)
    rows.sort(key=lambda row: (-row["buy_sol"], -row["sell_sol"], row["mint"]))
    return rows


_TRADE_KEYS = ("type", "timestamp", "sol_amount", "token_amount", "price", "signature")


def group_trades(trades: list[dict]) -> dict[str, list[dict]]:
    """Group wallet trades into one chronological list per mint."""
    grouped: dict[str, list[dict]] = {}
    for trade in trades:
        action = str(trade.get("action") or "")
        mint = str(trade.get("mint") or "")
        if action not in ("buy", "sell") or not mint:
            continue
        row = {"type": action}
        for key in _TRADE_KEYS:
            if key == "type":
                continue
            row[key] = trade.get(key)
        grouped.setdefault(mint, []).append(row)
    for rows in grouped.values():
        rows.sort(key=lambda row: (row.get("timestamp") or 0, row.get("signature") or ""))
    return grouped


def token_metadata(
    mints: list[str],
    trades: list[dict] | None = None,
    existing: dict[str, dict] | None = None,
) -> dict[str, dict]:
    """Jupiter name, symbol, and creation_time; description ticker as fallback."""
    names: dict[str, dict] = {}
    for mint in mints:
        info = (existing or {}).get(mint) or {}
        names[mint] = {
            "name": str(info.get("name") or "").strip(),
            "symbol": str(info.get("symbol") or "").strip(),
            "creation_time": info.get("creation_time"),
        }
    missing = [
        mint for mint in mints
        if not names[mint]["name"]
        or not names[mint]["symbol"]
        or not names[mint]["creation_time"]
    ]
    if missing:
        fetched = fetch_token_metadata(missing)
        for mint, info in fetched.items():
            prev = names.get(mint) or {}
            names[mint] = {
                "name": str(info.get("name") or prev.get("name") or "").strip(),
                "symbol": str(info.get("symbol") or prev.get("symbol") or "").strip(),
                "creation_time": info.get("creation_time") or prev.get("creation_time"),
            }
    for trade in trades or []:
        mint = str(trade.get("mint") or "")
        if not mint:
            continue
        info = names.get(mint) or {}
        if info.get("symbol"):
            continue
        symbol = _symbol_from_description(str(trade.get("description") or ""), mint)
        if symbol:
            names[mint] = {
                "name": info.get("name") or "",
                "symbol": symbol,
                "creation_time": info.get("creation_time"),
            }
    return names


def _symbol_from_description(description: str, mint: str) -> str:
    match = _DESC_BUY.search(description) or _DESC_SELL.search(description)
    if not match:
        return ""
    token = str(match.group(1) or "").strip()
    if not token or token == mint or len(token) >= 32:
        return ""
    return token


def save_wallet_scan(
    wallet: str,
    trades: list[dict],
    *,
    lookback_hours: float | None = None,
    meta: dict[str, dict] | None = None,
) -> Path:
    """Write one trades file per mint under var/trades/<wallet>/<mint>.json."""
    owner = wallet or TARGET_WALLET
    folder = Path(WALLET_TRADES_PATH) / owner
    legacy = Path(WALLET_TRADES_PATH) / f"{owner}.json"
    if legacy.is_file():
        legacy.unlink()
    folder.mkdir(parents=True, exist_ok=True)

    grouped = group_trades(trades)
    names = meta if meta is not None else token_metadata(list(grouped), trades)
    for mint, rows in grouped.items():
        info = names.get(mint) or {}
        payload = {
            "wallet": owner,
            "mint": mint,
            "name": info.get("name") or "",
            "symbol": info.get("symbol") or "",
            "creation_time": info.get("creation_time"),
            "trades": rows,
        }
        path = folder / f"{mint}.json"
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    logger.info(
        "saved wallet scan %s mints=%d trades=%d lookback=%s",
        folder,
        len(grouped),
        len(trades),
        lookback_hours if lookback_hours is not None else LOOKBACK_HOURS,
    )
    return folder


def load_wallet_scan(wallet: str) -> tuple[list[dict], dict[str, dict]]:
    """Load saved mint trade files under var/trades/<wallet>."""
    owner = wallet or TARGET_WALLET
    folder = Path(WALLET_TRADES_PATH) / owner
    trades: list[dict] = []
    meta: dict[str, dict] = {}
    if not folder.is_dir():
        return [], {}
    for path in sorted(folder.glob("*.json")):
        try:
            data = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        mint = str(data.get("mint") or path.stem).strip()
        if not mint:
            continue
        meta[mint] = {
            "name": str(data.get("name") or "").strip(),
            "symbol": str(data.get("symbol") or "").strip(),
            "creation_time": data.get("creation_time"),
        }
        for row in data.get("trades") or []:
            if not isinstance(row, dict):
                continue
            action = str(row.get("type") or row.get("action") or "")
            if action not in ("buy", "sell"):
                continue
            trades.append({
                "action": action,
                "mint": mint,
                "token_amount": row.get("token_amount"),
                "sol_amount": row.get("sol_amount"),
                "price": row.get("price"),
                "signature": str(row.get("signature") or ""),
                "timestamp": int(row.get("timestamp") or 0),
                "slot": int(row.get("slot") or 0),
                "source": str(row.get("source") or ""),
                "type": str(row.get("type") or action),
                "description": str(row.get("description") or ""),
            })
    trades.sort(key=lambda row: (row.get("timestamp") or 0, row.get("signature") or ""))
    return trades, meta


def _trade_key(trade: dict) -> tuple[str, str, str]:
    return (
        str(trade.get("signature") or ""),
        str(trade.get("mint") or ""),
        str(trade.get("action") or trade.get("type") or ""),
    )


def _merge_trades(saved: list[dict], extra: list[dict]) -> list[dict]:
    merged: dict[tuple[str, str, str], dict] = {}
    for trade in saved + extra:
        key = _trade_key(trade)
        if not key[0]:
            continue
        merged[key] = trade
    trades = list(merged.values())
    trades.sort(key=lambda row: (row.get("timestamp") or 0, row.get("signature") or ""))
    return trades


def fetch_wallet_transactions(
    wallet: str,
    *,
    time_from: int | None = None,
) -> list[dict]:
    """Page through Enhanced Transactions history, including ATA balance changes."""
    owner = wallet or TARGET_WALLET
    key = api_key()
    cursor = None
    rows = []
    while True:
        payload = _fetch_page(owner, key, cursor, time_from=time_from)
        if isinstance(payload, dict):
            cursor = _continue_signature(payload)
            if cursor:
                time.sleep(REQUEST_PAUSE_SEC)
                continue
            message = payload.get("error") or payload
            raise RuntimeError(f"Helius history error: {message}")
        if not payload:
            break
        in_window = [
            tx for tx in payload
            if time_from is None or int(tx.get("timestamp") or 0) >= time_from
        ]
        rows.extend(in_window)
        cursor = str(payload[-1].get("signature") or "")
        logger.info("helius page wallet=%s fetched=%d total=%d", owner, len(in_window), len(rows))
        if not cursor or len(payload) < PAGE_LIMIT:
            break
        if time_from and in_window and int(payload[-1].get("timestamp") or 0) < time_from:
            break
        if time_from and not in_window:
            break
        time.sleep(REQUEST_PAUSE_SEC)
    return rows


def parse_trades(tx: dict, wallet: str) -> list[dict]:
    """Return SOL buy/sell legs for the wallet in one parsed transaction."""
    if tx.get("transactionError"):
        return []
    received, sent, sol_in, sol_out = _wallet_sides(tx, wallet)
    mint = _primary_mint(received, sent)
    if not mint:
        return []
    buy_amt = received.get(mint, 0.0)
    sell_amt = sent.get(mint, 0.0)
    net = buy_amt - sell_amt
    gross = buy_amt + sell_amt
    if gross <= 0:
        return []
    rows = []
    if abs(net) / gross >= _MIN_NET_RATIO:
        if net > 0 and sol_out >= _MIN_SOL:
            rows.append(_trade_row(tx, "buy", mint, net, sol_out))
        elif net < 0 and sol_in >= _MIN_SOL:
            rows.append(_trade_row(tx, "sell", mint, -net, sol_in))
    else:
        if buy_amt > 0 and sol_out >= _MIN_SOL:
            rows.append(_trade_row(tx, "buy", mint, buy_amt, sol_out))
        if sell_amt > 0 and sol_in >= _MIN_SOL:
            rows.append(_trade_row(tx, "sell", mint, sell_amt, sol_in))
    return rows


def parse_trade(tx: dict, wallet: str) -> dict | None:
    """Classify a simple one-leg buy or sell; None when the tx has no single side."""
    rows = parse_trades(tx, wallet)
    return rows[0] if len(rows) == 1 else None


_MIN_SOL = 1e-5
_MIN_NET_RATIO = 0.25


def _trade_row(tx: dict, action: str, mint: str, token_amount: float, sol_amount: float) -> dict:
    return {
        "action": action,
        "mint": mint,
        "token_amount": token_amount,
        "sol_amount": sol_amount,
        "price": sol_amount / token_amount,
        "signature": str(tx.get("signature") or ""),
        "timestamp": int(tx.get("timestamp") or 0),
        "slot": int(tx.get("slot") or 0),
        "source": str(tx.get("source") or ""),
        "type": str(tx.get("type") or ""),
        "description": str(tx.get("description") or ""),
    }


def _wallet_sides(
    tx: dict, wallet: str,
) -> tuple[dict[str, float], dict[str, float], float, float]:
    received, sent, sol_in, sol_out = _swap_event_sides(tx, wallet)
    if received or sent or sol_in or sol_out:
        return received, sent, sol_in, sol_out
    return _transfer_sides(tx, wallet)


def _transfer_sides(
    tx: dict, wallet: str,
) -> tuple[dict[str, float], dict[str, float], float, float]:
    received: dict[str, float] = {}
    sent: dict[str, float] = {}
    wsol_in = 0.0
    wsol_out = 0.0
    for row in tx.get("tokenTransfers") or []:
        mint = str(row.get("mint") or "")
        if not mint or str(row.get("tokenStandard") or "") in _NFT_STANDARDS:
            continue
        amount = abs(to_float(row.get("tokenAmount")) or 0.0)
        if amount <= 0:
            continue
        sender = row.get("fromUserAccount") == wallet
        receiver = row.get("toUserAccount") == wallet
        if sender == receiver:
            continue
        if mint == SOL_ADDRESS:
            if sender:
                wsol_out += amount
            if receiver:
                wsol_in += amount
            continue
        if sender:
            sent[mint] = sent.get(mint, 0.0) + amount
        if receiver:
            received[mint] = received.get(mint, 0.0) + amount
    if wsol_in or wsol_out:
        return received, sent, wsol_in, wsol_out
    sol_in = _native_swap_sol(tx.get("nativeTransfers"), wallet, outgoing=False)
    sol_out = _native_swap_sol(tx.get("nativeTransfers"), wallet, outgoing=True)
    return received, sent, sol_in, sol_out


def _swap_event_sides(
    tx: dict, wallet: str,
) -> tuple[dict[str, float], dict[str, float], float, float]:
    swap = (tx.get("events") or {}).get("swap") or {}
    if not swap:
        return {}, {}, 0.0, 0.0
    sent = _wallet_tokens(swap.get("tokenInputs"), wallet)
    received = _wallet_tokens(swap.get("tokenOutputs"), wallet)
    native_out = _native_sol(swap.get("nativeInput"), wallet)
    native_in = _native_sol(swap.get("nativeOutput"), wallet)
    wsol_out = sent.pop(SOL_ADDRESS, 0.0)
    wsol_in = received.pop(SOL_ADDRESS, 0.0)
    sol_out = native_out if native_out else wsol_out
    sol_in = native_in if native_in else wsol_in
    return received, sent, sol_in, sol_out


def _native_swap_sol(rows: list | None, wallet: str, *, outgoing: bool) -> float:
    total = 0
    src = "fromUserAccount" if outgoing else "toUserAccount"
    dst = "toUserAccount" if outgoing else "fromUserAccount"
    for row in rows or []:
        if row.get(src) != wallet:
            continue
        if row.get(dst) == HELIUS_TIP_ACCOUNT:
            continue
        total += int(to_float(row.get("amount")) or 0)
    return total / LAMPORTS_PER_SOL


def _primary_mint(received: dict[str, float], sent: dict[str, float]) -> str | None:
    mints = set(received) | set(sent)
    mints.discard(SOL_ADDRESS)
    if not mints:
        return None
    return max(mints, key=lambda mint: received.get(mint, 0.0) + sent.get(mint, 0.0))


def _lookback_start(lookback_hours: float | None) -> int | None:
    hours = LOOKBACK_HOURS if lookback_hours is None else lookback_hours
    if hours is None or hours <= 0:
        return None
    return unix_now() - int(float(hours) * 3600)


def _fetch_page(
    wallet: str,
    key: str,
    before: str | None,
    *,
    time_from: int | None = None,
) -> list[dict] | dict:
    params = {
        "api-key": key,
        "limit": PAGE_LIMIT,
        "sort-order": "desc",
        "token-accounts": TOKEN_ACCOUNTS,
    }
    if time_from:
        params["gte-time"] = int(time_from)
    if before:
        params["before-signature"] = before
    response = _SESSION.get(
        HELIUS_TX_HISTORY_URL.format(address=wallet),
        params=params,
        timeout=RPC_REQUEST_TIMEOUT_SEC,
    )
    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError(
            f"Helius history invalid JSON ({response.status_code}): {response.text[:200]}"
        ) from exc
    if response.status_code >= 400 and not isinstance(payload, dict):
        raise RuntimeError(f"Helius history HTTP {response.status_code}: {payload}")
    return payload


def _continue_signature(payload: dict) -> str | None:
    error = payload.get("error")
    text = error if isinstance(error, str) else str(error or "")
    if "Failed to find events within the search period" not in text:
        return None
    match = _CONTINUE_SIG.search(text)
    return match.group(1) if match else None


def _native_sol(change: dict | None, wallet: str) -> float:
    if not isinstance(change, dict):
        return 0.0
    account = str(change.get("account") or "")
    if account and account != wallet:
        return 0.0
    return _lamports_to_sol(change.get("amount"))


def _wallet_tokens(rows: list | None, wallet: str) -> dict[str, float]:
    totals: dict[str, float] = {}
    for row in rows or []:
        if not isinstance(row, dict) or row.get("userAccount") != wallet:
            continue
        mint = str(row.get("mint") or "")
        amount = _raw_token_amount(row.get("rawTokenAmount"))
        if not mint or amount <= 0:
            continue
        totals[mint] = totals.get(mint, 0.0) + amount
    return totals


def _raw_token_amount(raw: dict | None) -> float:
    if not isinstance(raw, dict):
        return 0.0
    text = str(raw.get("tokenAmount") or "0").strip()
    amount = abs(to_float(text) or 0.0)
    decimals = int(to_float(raw.get("decimals")) or 0)
    if "." in text or decimals <= 0:
        return amount
    return amount / (10 ** decimals)


def _lamports_to_sol(value: object) -> float:
    lamports = abs(to_float(value) or 0.0)
    return lamports / LAMPORTS_PER_SOL
