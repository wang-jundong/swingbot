"""Transaction history (CSV)."""

from pathlib import Path
from typing import Optional

import pandas as pd

from src.config.history import TRANSACTION_COLUMNS
from src.config.bindings.paths import TRANSACTION_HISTORY_PATHS
from src.config.trading import HOLD_DAYS
from src.storage.settings import get_key_id
from src.utils.number_util import format_decimal
from src.utils.time_util import str_to_unix, unix_now, unix_to_str
from src.utils.log_util import get_dex_logger

logger = get_dex_logger()


def _history_path(filepath: Optional[Path | str] = None) -> Path:
    if filepath:
        return Path(filepath)
    key_id = get_key_id()
    return Path(TRANSACTION_HISTORY_PATHS.get(key_id, TRANSACTION_HISTORY_PATHS["solana"]))


def _ensure_file_exists(path: Path) -> None:
    """Create file with headers if missing."""
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(columns=TRANSACTION_COLUMNS).to_csv(path, index=False)


def _net_cost_for_symbol(df: pd.DataFrame, symbol: str) -> float:
    """Net native cost: buy - sell."""
    mask = df["symbol"] == symbol
    if not mask.any():
        return 0.0
    rows = df[mask]
    total_buy = rows.loc[rows["action"] == "buy", "amount"].astype(float).sum()
    total_sell = rows.loc[rows["action"] == "sell", "amount"].astype(float).sum()
    return float(total_buy - total_sell)


def pnl_native(price: float | None, balance: float | None, net_cost: float) -> float | None:
    """Unrealized PnL: current value minus net buy cost."""
    if price is None or balance is None:
        return None
    return (price * balance) - net_cost


def get_pending_transactions(filepath: Optional[Path | str] = None) -> dict[str, dict]:
    """Pending transactions per symbol."""
    path = _history_path(filepath)
    if not path.exists():
        return {}

    df = pd.read_csv(path)

    mask = df["status"] == "pending"
    if not mask.any():
        return {}

    df = df[mask]
    rows = df.to_dict("records")
    result: dict[str, dict] = {}
    for row in rows:
        sym = row.get("symbol", "?")
        if sym not in result:
            result[sym] = {"rows": [], "net_cost": _net_cost_for_symbol(df, sym)}
        result[sym]["rows"].append(row)

    return result


def get_pending_buy_transactions_by_symbol(
    symbol: str,
    filepath: Optional[Path | str] = None,
) -> list[dict]:
    """Pending buy transactions for a specific symbol."""
    symbol_pending = get_pending_transactions(filepath=filepath).get(symbol, {})
    return [
        row
        for row in symbol_pending.get("rows", [])
        if str(row.get("action", "")).lower() == "buy"
    ]


def is_hold_expired(buys: list[dict]) -> bool:
    """True when the first pending buy is at least HOLD_DAYS old."""
    if not buys:
        return False
    first = min(buys, key=lambda row: str(row.get("timestamp") or ""))
    started = str_to_unix(first.get("timestamp"))
    if started is None:
        return False
    return unix_now() - started >= HOLD_DAYS * 86400


def save_transaction(
    action: str,
    symbol: str,
    amount: float,
    price: float,
    tx_hash: str,
    status: str = "pending",
    pnl: float = 0.0,
    filepath: Optional[Path | str] = None,
) -> None:
    """Append transaction to the CSV."""
    path = _history_path(filepath)
    _ensure_file_exists(path)

    row = {
        "timestamp": unix_to_str(unix_now()),
        "action": action,
        "symbol": symbol,
        "amount": format_decimal(amount),
        "price": format_decimal(price),
        "tx_hash": tx_hash,
        "status": status,
        "pnl": format_decimal(pnl),
    }

    new_df = pd.DataFrame([row], columns=TRANSACTION_COLUMNS)

    if path.exists() and path.stat().st_size > 0:
        existing = pd.read_csv(path)
        combined = pd.concat([existing, new_df], ignore_index=True)
        combined = combined.reindex(columns=TRANSACTION_COLUMNS)
    else:
        combined = new_df

    combined.to_csv(path, index=False)
    logger.info("Saved transaction to %s: %s %s %s", path, action, symbol, tx_hash)


def remove_pending_transactions(
    symbol: str,
    filepath: Optional[Path | str] = None,
) -> int:
    """Delete all pending rows for symbol. Returns number of rows removed."""
    path = _history_path(filepath)
    if not path.exists():
        return 0

    df = pd.read_csv(path)
    mask = (df["symbol"] == symbol) & (df["status"] == "pending")
    removed = int(mask.sum())
    if removed:
        df[~mask].to_csv(path, index=False)
        logger.info("Removed %d pending row(s) for %s", removed, symbol)
    return removed


def close_symbol_and_calculate_pnl(
    symbol: str,
    amount_native_received: float = 0.0,
    filepath: Optional[Path | str] = None,
) -> tuple[float, float, float, int]:
    """Delete symbol rows; return (pnl, total_buy, total_sell, buy_count). PnL = sell - buy."""
    path = _history_path(filepath)
    if not path.exists():
        total_sell = float(amount_native_received)
        return total_sell, 0.0, total_sell, 0

    df = pd.read_csv(path)
    symbol_mask = df["symbol"] == symbol
    if not symbol_mask.any():
        total_sell = float(amount_native_received)
        return total_sell, 0.0, total_sell, 0

    pending = df[symbol_mask & (df["status"] == "pending")]
    buy_count = int((pending["action"] == "buy").sum())
    total_buy = float(
        pending.loc[pending["action"] == "buy", "amount"].astype(float).sum()
    )
    total_sell = float(
        pending.loc[pending["action"] == "sell", "amount"].astype(float).sum()
    )
    total_sell += float(amount_native_received)

    removed = int(symbol_mask.sum())
    df[~symbol_mask].to_csv(path, index=False)

    pnl = total_sell - total_buy
    logger.info(
        "Closed %s: removed %d row(s), buy=%.6f sell=%.6f pnl=%.6f buy_count=%d",
        symbol,
        removed,
        total_buy,
        total_sell,
        pnl,
        buy_count,
    )
    return pnl, total_buy, total_sell, buy_count
