"""Load wallet OHLC files as backtest datasets."""

from __future__ import annotations

from pathlib import Path

from src.config.backtest import INTERVAL
from src.config.track import TARGET_WALLET
from src.storage.ohlc import INTERVALS, _aggregate, _load_candles, list_wallets, ohlc_root, safe_id


def resolve_wallet(wallet: str | None) -> str | None:
    wanted = safe_id(wallet) or safe_id(TARGET_WALLET)
    folders = list_wallets()
    if wanted and wanted in folders:
        return wanted
    return folders[0] if folders else None


def discover_mints(wallet: str | None = None, mint: str | None = None) -> list[dict]:
    owner = resolve_wallet(wallet)
    if owner is None:
        return []
    folder = ohlc_root() / owner
    wanted = safe_id(mint)
    rows: list[dict] = []
    for path in sorted(folder.glob("*.json")):
        token = safe_id(path.stem)
        if token is None:
            continue
        if wanted and token != wanted:
            continue
        candles = load_bars(path)
        if not candles:
            continue
        rows.append({
            "mint": token,
            "wallet": owner,
            "symbol": "",
            "path": str(path),
            "candles": candles,
        })
    return rows


def load_bars(path: Path, interval: str | None = None) -> list[dict]:
    candles = _load_candles(path)
    if not candles:
        return []
    key = interval or INTERVAL
    step = INTERVALS.get(key, 60)
    return _aggregate(candles, step)
