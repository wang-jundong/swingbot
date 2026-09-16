"""Read the last backtest run for the dashboard."""

from __future__ import annotations

import json
from pathlib import Path

from src.config.bindings.paths import BACKTEST_PATH


def empty_stats() -> dict:
    return {
        "realized_pnl": 0.0,
        "unrealized_pnl": 0.0,
        "total_pnl": 0.0,
        "wins": 0,
        "losses": 0,
        "trades": 0,
        "fees_total": 0.0,
    }


def load_last() -> dict | None:
    path = Path(BACKTEST_PATH) / "last.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def dashboard_stats(wallet: str | None = None, mint: str | None = None) -> dict:
    return stats_from_trades(_trades(wallet, mint))


def mint_stats(wallet: str | None = None) -> dict[str, dict]:
    rows: dict[str, list[dict]] = {}
    for trade in _trades(wallet, None):
        mint = str(trade.get("mint") or "")
        if not mint:
            continue
        rows.setdefault(mint, []).append(trade)
    return {mint: stats_from_trades(items) for mint, items in rows.items()}


def _trades(wallet: str | None, mint: str | None) -> list[dict]:
    data = load_last()
    if not data:
        return []
    trades: list[dict] = []
    for row in data.get("mints") or []:
        if not isinstance(row, dict):
            continue
        if wallet and row.get("wallet") and row.get("wallet") != wallet:
            continue
        if mint and row.get("mint") != mint:
            continue
        for trade in row.get("trades") or []:
            if isinstance(trade, dict):
                trades.append(trade)
    return trades


def me_marks(wallet: str | None = None, mint: str | None = None) -> list[dict]:
    marks: list[dict] = []
    for trade in _trades(wallet, mint):
        buy_t = trade.get("buy_t")
        if buy_t:
            marks.append({
                "t": int(buy_t),
                "side": "buy",
                "price": trade.get("buy_price"),
                "reason": str(trade.get("buy_reason") or ""),
            })
        sell_t = trade.get("sell_t")
        if sell_t:
            marks.append({
                "t": int(sell_t),
                "side": "sell",
                "price": trade.get("sell_price"),
                "reason": str(trade.get("sell_reason") or ""),
                "pnl_sol": trade.get("pnl_sol"),
            })
    marks.sort(key=lambda row: row["t"])
    return marks


def stats_from_trades(trades: list[dict]) -> dict:
    closed = [trade for trade in trades if trade.get("status") == "closed"]
    realized = [trade for trade in closed if trade.get("sell_reason") != "EOT"]
    unrealized = [trade for trade in closed if trade.get("sell_reason") == "EOT"]
    wins = [trade for trade in closed if (trade.get("pnl_sol") or 0) > 0]
    losses = [trade for trade in closed if (trade.get("pnl_sol") or 0) <= 0]
    realized_pnl = sum(float(trade.get("pnl_sol") or 0) for trade in realized)
    unrealized_pnl = sum(float(trade.get("pnl_sol") or 0) for trade in unrealized)
    return {
        "realized_pnl": realized_pnl,
        "unrealized_pnl": unrealized_pnl,
        "total_pnl": realized_pnl + unrealized_pnl,
        "wins": len(wins),
        "losses": len(losses),
        "trades": len(closed),
        "fees_total": sum(float(trade.get("fees_sol") or 0) for trade in closed),
    }
