"""Run the OHLC structure backtest across discovered mints."""

from __future__ import annotations

from src.backtest.data import discover_mints
from src.backtest.execution import buy_fill, close_fill, sell_fill
from src.backtest.models import MintResult, Summary, Trade
from src.backtest.portfolio import close_position, open_position
from src.backtest.strategy import buy_reason, sell_reason
from src.backtest.walk import walk_bars
from src.config.backtest import FLATTEN_EOT, MAX_BUYS, MAX_MINTS, POSITION_SIZE_SOL, as_dict


def run_backtest(wallet: str | None = None, mint: str | None = None) -> tuple[Summary, list[MintResult]]:
    datasets = discover_mints(wallet, mint)
    if MAX_MINTS > 0:
        datasets = datasets[:MAX_MINTS]
    results = [run_mint(row) for row in datasets]
    return summarize(results), results


def run_mint(row: dict) -> MintResult:
    candles = row["candles"]
    result = MintResult(
        mint=row["mint"],
        symbol=row.get("symbol") or "",
        wallet=row["wallet"],
        bars=len(candles),
    )
    snapshots = walk_bars(candles)
    position = None
    open_trade: Trade | None = None
    buys = 0

    for snap in snapshots:
        i = snap["i"]
        last_bar = i >= len(candles) - 1
        next_bar = None if last_bar else candles[i + 1]

        if position is not None and open_trade is not None:
            reason = sell_reason(snap, position, FLATTEN_EOT, last_bar)
            if reason:
                result.sell_signals += 1
                fill = close_fill(candles[i], position.tokens) if last_bar else sell_fill(next_bar, position.tokens)
                if fill:
                    close_position(position, open_trade, fill, reason)
                    result.trades.append(open_trade)
                position = None
                open_trade = None
                continue

        reason = buy_reason(snap, buys, MAX_BUYS, position is not None)
        if not reason:
            continue
        result.buy_signals += 1
        if last_bar:
            continue
        fill = buy_fill(next_bar, POSITION_SIZE_SOL)
        if fill is None:
            continue
        buys += 1
        position, open_trade = open_position(row["mint"], result.symbol, fill, reason, i)

    if position is not None and open_trade is not None and candles:
        fill = close_fill(candles[-1], position.tokens)
        if fill:
            close_position(position, open_trade, fill, "EOT")
            result.trades.append(open_trade)
    return result


def summarize(results: list[MintResult]) -> Summary:
    trades = [trade for row in results for trade in row.trades]
    closed = [trade for trade in trades if trade.status == "closed"]
    eot = [trade for trade in closed if trade.sell_reason == "EOT"]
    wins = [trade for trade in closed if (trade.pnl_sol or 0) > 0]
    losses = [trade for trade in closed if (trade.pnl_sol or 0) <= 0]
    realized_pnl = sum(trade.pnl_sol or 0.0 for trade in closed if trade not in eot)
    unrealized_pnl = sum(trade.pnl_sol or 0.0 for trade in eot)
    return Summary(
        mints=len(results),
        bars=sum(row.bars for row in results),
        trades=len(closed),
        closed=len(closed) - len(eot),
        eot=len(eot),
        wins=len(wins),
        losses=len(losses),
        win_rate=(len(wins) / len(closed) * 100.0) if closed else 0.0,
        realized_pnl_sol=realized_pnl,
        unrealized_pnl_sol=unrealized_pnl,
        pnl_sol=realized_pnl + unrealized_pnl,
        avg_win_sol=(sum(trade.pnl_sol or 0.0 for trade in wins) / len(wins)) if wins else 0.0,
        avg_loss_sol=(sum(trade.pnl_sol or 0.0 for trade in losses) / len(losses)) if losses else 0.0,
        fees_sol=sum(trade.fees_sol for trade in closed),
        buy_signals=sum(row.buy_signals for row in results),
        sell_signals=sum(row.sell_signals for row in results),
    )


def export_payload(summary: Summary, results: list[MintResult]) -> dict:
    return {
        "config": as_dict(),
        "summary": summary.to_dict(),
        "mints": [
            {
                "mint": row.mint,
                "symbol": row.symbol,
                "wallet": row.wallet,
                "bars": row.bars,
                "buy_signals": row.buy_signals,
                "sell_signals": row.sell_signals,
                "trades": [trade.to_dict() for trade in row.trades],
            }
            for row in results
            if row.trades or row.buy_signals
        ],
    }
