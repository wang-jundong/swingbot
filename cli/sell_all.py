"""CLI: sell every pending token from transaction history."""

import sys

from src.config.trading import SWING_SELL_AMOUNT
from src.dex.history.trade_stats import REASON_MANUAL
from src.dex.history.transaction import get_pending_transactions
from src.dex.solana.client import DexClient
from src.dex.solana.common.spl import get_owner_token_balances
from src.storage.coins import get_all_tokens
from src.utils.number_util import format_decimal


def main() -> int:
    pending = get_pending_transactions()
    if not pending:
        print("no pending tokens")
        return 0

    coins_by_symbol = {
        str(coin.get("symbol") or "").strip(): coin
        for coin in get_all_tokens()
    }
    client = DexClient()
    balances = get_owner_token_balances(
        client.rpc_url,
        str(client.keypair.pubkey()),
    )

    print(f"selling {len(pending)} token(s)")
    sold = 0
    skipped = 0
    failed = 0

    for symbol in pending:
        coin = coins_by_symbol.get(str(symbol).strip())
        mint = (coin or {}).get("address")
        if not mint:
            print(f"skip {symbol}: unknown token")
            skipped += 1
            continue

        balance = balances.get(mint, 0.0)
        if balance <= 0:
            print(f"skip {symbol}: no balance")
            skipped += 1
            continue

        try:
            tx_hash, success, pnl, _before, _after = client.sell(
                symbol, SWING_SELL_AMOUNT, reason=REASON_MANUAL,
            )
        except Exception as exc:
            print(f"fail {symbol}: {exc}")
            failed += 1
            continue

        if success and tx_hash:
            print(f"sold {symbol} pnl={format_decimal(pnl)} {tx_hash}")
            sold += 1
        else:
            print(f"fail {symbol}")
            failed += 1

    print(f"done sold={sold} skipped={skipped} failed={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
