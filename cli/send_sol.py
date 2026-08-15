"""CLI entry point to send native SOL or an SPL memecoin."""

import sys

from src.dex.solana.common.transfer import send_native_sol, send_token

RECIPIENT = ""
AMOUNT = 0.0
SYMBOL = None  # e.g. "BONK" to send meme token; None for native SOL


def main() -> int:
    if SYMBOL:
        tx = send_token(SYMBOL, AMOUNT, RECIPIENT)
    else:
        tx = send_native_sol(AMOUNT, RECIPIENT)
    if not tx:
        return 1
    print(tx)
    return 0


if __name__ == "__main__":
    sys.exit(main())
