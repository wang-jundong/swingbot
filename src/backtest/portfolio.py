"""One position per mint and closed-trade accounting."""

from __future__ import annotations

from src.backtest.models import Position, Trade


def open_position(mint: str, symbol: str, fill: dict, reason: str, bar_i: int) -> tuple[Position, Trade]:
    position = Position(
        mint=mint,
        buy_i=bar_i,
        buy_t=fill["t"],
        buy_price=fill["price"],
        tokens=fill["tokens"],
        cost_sol=fill["sol"],
        reason=reason,
        fees_sol=fill["fee"],
    )
    trade = Trade(
        mint=mint,
        symbol=symbol,
        status="open",
        buy_t=fill["t"],
        buy_price=fill["price"],
        buy_reason=reason,
        cost_sol=fill["sol"],
        tokens=fill["tokens"],
        fees_sol=fill["fee"],
    )
    return position, trade


def close_position(position: Position, trade: Trade, fill: dict, reason: str) -> Trade:
    pnl = fill["sol"] - position.cost_sol
    trade.status = "closed"
    trade.sell_t = fill["t"]
    trade.sell_price = fill["price"]
    trade.sell_reason = reason
    trade.proceeds_sol = fill["sol"]
    trade.pnl_sol = pnl
    trade.pnl_pct = (pnl / position.cost_sol * 100.0) if position.cost_sol else 0.0
    trade.fees_sol = position.fees_sol + fill["fee"]
    return trade


def mark_pnl(position: Position, close: float) -> float:
    if close <= 0:
        return 0.0
    return position.tokens * close - position.cost_sol
