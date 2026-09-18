"""Read source-wallet entries for chart annotations."""

import json
from pathlib import Path

from src.config.bindings.paths import WALLET_TRADES_PATH
from src.storage.ohlc import safe_id


def first_wallet_entry(wallet: str, mint: str) -> dict | None:
    """Earliest buy, or earliest sell when no buys were saved."""
    owner, token = safe_id(wallet), safe_id(mint)
    if not owner or not token:
        return None
    path = Path(WALLET_TRADES_PATH) / owner / f"{token}.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    times = {"buy": [], "sell": []}
    for trade in payload.get("trades") or []:
        if not isinstance(trade, dict):
            continue
        side = trade.get("type")
        if side not in times:
            continue
        try:
            timestamp = int(trade["timestamp"])
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        if timestamp > 0:
            times[side].append(timestamp)
    for side in ("buy", "sell"):
        if times[side]:
            return {"t": min(times[side]), "side": side}
    return None
