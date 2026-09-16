"""CLI: run the OHLC structure backtest.

Usage:
  python cli/backtest.py
  python cli/backtest.py <WALLET>
  python cli/backtest.py <WALLET> <MINT>
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.backtest.data import resolve_wallet
from src.backtest.export import write_results
from src.backtest.runner import export_payload, run_backtest
from src.config.backtest import INTERVAL, STRATEGY
from src.utils.number_util import format_decimal


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    wallet = args[0] if args else None
    mint = args[1] if len(args) > 1 else None
    owner = resolve_wallet(wallet)
    if owner is None:
        print("no OHLC wallets in var/ohlc")
        return 1
    summary, results = run_backtest(owner, mint)
    path = write_results(export_payload(summary, results))
    print(
        f"wallet={owner} interval={INTERVAL} strategy={STRATEGY} "
        f"mints={summary.mints} bars={summary.bars} "
        f"trades={summary.trades} closed={summary.closed} eot={summary.eot} "
        f"wins={summary.wins} losses={summary.losses} "
        f"win_rate={summary.win_rate:.1f}% "
        f"pnl={format_decimal(summary.pnl_sol)} "
        f"fees={format_decimal(summary.fees_sol)}"
    )
    closed = [trade for row in results for trade in row.trades]
    for trade in closed[:20]:
        pnl = format_decimal(trade.pnl_sol or 0.0)
        print(
            f"mint={trade.mint} {trade.buy_reason} -> {trade.sell_reason} "
            f"pnl={pnl}"
        )
    if len(closed) > 20:
        print(f"... {len(closed) - 20} more trades")
    print(f"saved {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
