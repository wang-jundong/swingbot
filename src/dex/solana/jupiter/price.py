"""Jupiter spot price in SOL per token."""

from __future__ import annotations

from src.dex.solana.common.spl import human_to_raw
from src.dex.solana.common.swap import get_swap_context
from src.config.solana import SOL_ADDRESS, SOL_DECIMALS
from src.dex.solana.jupiter.quotes import quote_out_amount


def get_price_sol(symbol: str) -> float | None:
    """Return spot price in SOL per 1 token."""
    ctx = get_swap_context(symbol)
    if not ctx:
        return None

    keypair, coin, _rpc_url, token_decimals = ctx
    owner = str(keypair.pubkey())
    input_address = coin["address"]

    try:
        input_raw = human_to_raw(1.0, token_decimals)
    except ValueError:
        return None

    return quote_out_amount(
        owner,
        input_address,
        SOL_ADDRESS,
        input_raw,
        SOL_DECIMALS,
        dexes=coin.get("dexes"),
    )
