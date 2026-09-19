"""CLI: scan all buy/sell swaps of TARGET_WALLET via Helius."""

import sys

from src.config.track import LOOKBACK_HOURS, MAX_TOKEN_AGE_DAYS, TARGET_WALLET
from src.integrations.helius import (
    aggregate_trades,
    group_trades,
    save_wallet_scan,
    scan_wallet_trades,
)
from src.utils.number_util import format_decimal
from src.utils.time_util import unix_to_str


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    wallet = args[0] if args else TARGET_WALLET
    trades, stats = scan_wallet_trades(wallet, lookback_hours=LOOKBACK_HOURS)
    rows = aggregate_trades(trades)
    grouped = group_trades(trades)
    meta = stats["meta"]
    buys = sum(1 for trade in trades if trade.get("action") == "buy")
    sells = sum(1 for trade in trades if trade.get("action") == "sell")
    spent = sum(row["buy_sol"] for row in rows)
    received = sum(row["sell_sol"] for row in rows)
    lookback = f"{LOOKBACK_HOURS:g}h" if LOOKBACK_HOURS else "all"
    print(
        f"wallet={wallet} lookback={lookback} mints={len(rows)} "
        f"max_token_age_days={MAX_TOKEN_AGE_DAYS:g} "
        f"skipped_old_mints={stats['skipped_old_mints']} "
        f"unknown_age_mints={stats['unknown_age_mints']} "
        f"buys={buys} sells={sells} "
        f"spent={format_decimal(spent)} received={format_decimal(received)}"
        + (f" added={stats.get('added') or 0} resumed" if stats.get("resumed") else "")
    )
    for row in rows:
        mint = row["mint"]
        info = meta.get(mint) or {}
        symbol = info.get("symbol") or ""
        name = info.get("name") or ""
        extra = " ".join(part for part in (symbol, name) if part)
        created = info.get("creation_time")
        created_s = f" created={unix_to_str(created)}" if created else ""
        print(f"mint={mint}" + (f" {extra}" if extra else "") + created_s)
        for trade in grouped.get(mint) or []:
            print(_format_side(str(trade.get("type") or ""), trade))
    path = save_wallet_scan(wallet, trades, lookback_hours=LOOKBACK_HOURS, meta=meta)
    print(f"saved {path}")
    return 0


def _format_side(action: str, trade: dict) -> str:
    ts = unix_to_str(trade["timestamp"]) if trade.get("timestamp") else "?"
    return (
        f"{action:<4} {ts} "
        f"sol={format_decimal(trade.get('sol_amount') or 0.0)} "
        f"token={format_decimal(trade.get('token_amount') or 0.0)} "
        f"px={format_decimal(trade.get('price') or 0.0)}"
    )


if __name__ == "__main__":
    sys.exit(main())
