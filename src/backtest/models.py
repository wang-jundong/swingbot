"""Backtest trades and aggregate stats."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Position:
    mint: str
    buy_i: int
    buy_t: int
    buy_price: float
    tokens: float
    cost_sol: float
    reason: str
    fees_sol: float = 0.0


@dataclass
class Trade:
    mint: str
    symbol: str
    status: str
    buy_t: int
    buy_price: float
    buy_reason: str
    cost_sol: float
    tokens: float
    sell_t: int | None = None
    sell_price: float | None = None
    sell_reason: str = ""
    proceeds_sol: float | None = None
    pnl_sol: float | None = None
    pnl_pct: float | None = None
    fees_sol: float = 0.0

    def to_dict(self) -> dict:
        return {
            "mint": self.mint,
            "symbol": self.symbol,
            "status": self.status,
            "buy_t": self.buy_t,
            "buy_price": self.buy_price,
            "buy_reason": self.buy_reason,
            "cost_sol": self.cost_sol,
            "tokens": self.tokens,
            "sell_t": self.sell_t,
            "sell_price": self.sell_price,
            "sell_reason": self.sell_reason,
            "proceeds_sol": self.proceeds_sol,
            "pnl_sol": self.pnl_sol,
            "pnl_pct": self.pnl_pct,
            "fees_sol": self.fees_sol,
        }


@dataclass
class MintResult:
    mint: str
    symbol: str
    wallet: str
    bars: int
    trades: list[Trade] = field(default_factory=list)
    buy_signals: int = 0
    sell_signals: int = 0


@dataclass
class Summary:
    mints: int = 0
    bars: int = 0
    trades: int = 0
    closed: int = 0
    eot: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    realized_pnl_sol: float = 0.0
    unrealized_pnl_sol: float = 0.0
    pnl_sol: float = 0.0
    avg_win_sol: float = 0.0
    avg_loss_sol: float = 0.0
    fees_sol: float = 0.0
    buy_signals: int = 0
    sell_signals: int = 0

    def to_dict(self) -> dict:
        return {
            "mints": self.mints,
            "bars": self.bars,
            "trades": self.trades,
            "closed": self.closed,
            "eot": self.eot,
            "wins": self.wins,
            "losses": self.losses,
            "win_rate": self.win_rate,
            "realized_pnl": self.realized_pnl_sol,
            "unrealized_pnl": self.unrealized_pnl_sol,
            "total_pnl": self.pnl_sol,
            "pnl_sol": self.pnl_sol,
            "avg_win_sol": self.avg_win_sol,
            "avg_loss_sol": self.avg_loss_sol,
            "fees_sol": self.fees_sol,
            "fees_total": self.fees_sol,
            "buy_signals": self.buy_signals,
            "sell_signals": self.sell_signals,
        }
