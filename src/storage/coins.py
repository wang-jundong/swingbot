"""Unified coin loading and queries."""

import fcntl
import json
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from src.config.bindings.paths import COINS_PATH
from src.utils.address_util import normalize_coin
from src.utils.number_util import rounded
from src.utils.time_util import unix_now, unix_to_str

_thread_lock = threading.Lock()


def _lock_path(path: Path) -> Path:
    return path.with_name(f"{path.name}.lock")


@contextmanager
def _coins_lock(path: Path) -> Iterator[None]:
    """Serialize coins access within the process and across processes."""
    lock_file_path = _lock_path(path)
    lock_file_path.parent.mkdir(parents=True, exist_ok=True)
    with _thread_lock:
        with open(lock_file_path, "w") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _load_unlocked(path: Path) -> list[dict]:
    """Load coins from JSON. Missing or invalid file → empty list."""
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        return [normalize_coin(c) for c in data]
    except Exception:
        return []


def _save_unlocked(path: Path, coins: list[dict]) -> None:
    """Persist coins to JSON atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    _uniquify_symbols(coins)
    payload = json.dumps(coins, indent=2, ensure_ascii=False)
    tmp = path.with_suffix(f"{path.suffix}.tmp")
    tmp.write_text(payload)
    tmp.replace(path)


def load_coins(filepath: Optional[str] = None) -> list[dict]:
    path = Path(filepath or COINS_PATH)
    with _coins_lock(path):
        return _load_unlocked(path)


def save_coins(coins: list[dict], filepath: Optional[str] = None) -> None:
    """Persist coins to JSON."""
    path = Path(filepath or COINS_PATH)
    with _coins_lock(path):
        _save_unlocked(path, coins)


def get_all_tokens() -> list[dict]:
    """All coins."""
    return load_coins()


def get_coin_by_symbol(symbol: str) -> Optional[dict]:
    """Return coin dict for symbol or None (loads from file)."""
    for c in load_coins():
        if c.get("symbol") == symbol:
            return c
    return None


def upsert_scanned_tokens(
    tokens: list[dict],
    filepath: Optional[str] = None,
) -> tuple[list[dict], int]:
    """Save scanned tokens that are not already stored by address."""
    path = Path(filepath or COINS_PATH)
    with _coins_lock(path):
        coins = _load_unlocked(path)
        renamed = _uniquify_symbols(coins)
        by_address = {c["address"]: c for c in coins if c.get("address")}
        taken = {c["symbol"] for c in coins if c.get("symbol")}
        scanned = []
        added = 0

        for token in tokens:
            address = token.get("address")
            if not address:
                continue

            coin = by_address.get(address)
            if coin is None:
                symbol = _unique_symbol(token.get("symbol") or "UNK", taken)
                taken.add(symbol)
                coin = {
                    "name": token.get("name") or symbol,
                    "symbol": symbol,
                    "address": address,
                }
                coins.append(coin)
                by_address[address] = coin
                added += 1

            _increment_scan_count(coin)
            scanned.append({
                **coin,
                "liquidity_usd": token.get("liquidity_usd"),
                "pair_age_days": token.get("pair_age_days"),
                "filter_reason": token.get("filter_reason"),
            })

        if added or renamed or scanned:
            _save_unlocked(path, coins)
        return scanned, added


def append_buy_metrics(
    address: str,
    liquidity: float | None,
    pair_age: float | None,
    filter_reason: str | None,
    buy_time: str | None,
    filepath: Optional[str] = None,
) -> None:
    """Append liquidity, pair age, and filter match from a buy onto the stored coin."""
    path = Path(filepath or COINS_PATH)
    with _coins_lock(path):
        coins = _load_unlocked(path)
        for coin in coins:
            if coin.get("address") != address:
                continue
            coin["liquidity"] = _as_list(coin.get("liquidity"))
            coin["pair_age"] = _as_list(coin.get("pair_age"))
            coin["filter_reason"] = _as_list(coin.get("filter_reason"))
            coin["buy_time"] = _as_list(coin.get("buy_time"))
            coin["liquidity"].append(rounded(liquidity, 2))
            coin["pair_age"].append(rounded(pair_age, 2))
            coin["filter_reason"].append(filter_reason)
            coin["buy_time"].append(buy_time)
            _save_unlocked(path, coins)
            return


def append_sell_metrics(
    symbol: str,
    pnl: float | None,
    reason: str | None,
    filepath: Optional[str] = None,
) -> None:
    """Append realized PnL, sell reason, and sell time onto the stored coin."""
    path = Path(filepath or COINS_PATH)
    with _coins_lock(path):
        coins = _load_unlocked(path)
        for coin in coins:
            if coin.get("symbol") != symbol:
                continue
            coin["pnl"] = _as_list(coin.get("pnl"))
            coin["sell_reason"] = _as_list(coin.get("sell_reason"))
            coin["sell_time"] = _as_list(coin.get("sell_time"))
            coin["pnl"].append(rounded(pnl, 4))
            coin["sell_reason"].append(reason)
            coin["sell_time"].append(unix_to_str(unix_now()))
            _save_unlocked(path, coins)
            return


def _as_list(value) -> list:
    if isinstance(value, list):
        return list(value)
    if value is None:
        return []
    return [value]


def _increment_scan_count(coin: dict) -> None:
    """Add to the open scan-match round, or start a new one after a sell."""
    counts = _as_list(coin.get("scan_count"))
    if len(counts) <= len(_as_list(coin.get("sell_time"))):
        counts.append(1)
    else:
        counts[-1] = int(counts[-1] or 0) + 1
    coin["scan_count"] = counts


def _unique_symbol(symbol: str, taken: set[str]) -> str:
    if symbol not in taken:
        return symbol
    n = 2
    while f"{symbol}_{n}" in taken:
        n += 1
    return f"{symbol}_{n}"


def _uniquify_symbols(coins: list[dict]) -> bool:
    taken: set[str] = set()
    changed = False
    for coin in coins:
        symbol = coin.get("symbol") or "UNK"
        unique = _unique_symbol(symbol, taken)
        taken.add(unique)
        if coin.get("symbol") != unique:
            coin["symbol"] = unique
            changed = True
    return changed
