"""CLI: fetch Birdeye OHLCV for every scanned mint in a wallet."""

import sys

from src.config.birdeye import OHLC_INTERVAL
from src.config.track import LOOKBACK_HOURS, TARGET_WALLET
from src.integrations.birdeye import export_wallet_ohlc
from src.utils.time_util import unix_to_str


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    wallet = args[0] if args else TARGET_WALLET
    folder, rows = export_wallet_ohlc(wallet, lookback_hours=LOOKBACK_HOURS)
    failed = sum(1 for row in rows if row.get("error"))
    lookback = f"{LOOKBACK_HOURS:g}h" if LOOKBACK_HOURS else "trades"
    print(
        f"wallet={wallet} lookback={lookback} interval={OHLC_INTERVAL} "
        f"mints={len(rows)} failed={failed}"
    )
    for row in rows:
        mint = row["mint"]
        extra = " ".join(part for part in (row.get("symbol"), row.get("name")) if part)
        if row.get("error"):
            print(f"mint={mint}" + (f" {extra}" if extra else "") + " error")
            continue
        start = unix_to_str(row["time_from"]) if row.get("time_from") else "?"
        end = unix_to_str(row["time_to"]) if row.get("time_to") else "?"
        print(
            f"mint={mint}"
            + (f" {extra}" if extra else "")
            + f" candles={row.get('candles') or 0}"
            + (f" added={row.get('added') or 0} resumed" if row.get("resumed") else "")
            + f" from={start} to={end}"
        )
    print(f"saved {folder}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
