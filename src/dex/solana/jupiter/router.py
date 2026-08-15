"""Jupiter buy / sell router."""

from __future__ import annotations

from typing import Optional, Tuple, Union

from src.dex.solana.common.swap import get_swap_context, resolve_sell_amount_raw
from src.config.solana import LAMPORTS_PER_SOL, SOL_ADDRESS, SOL_DECIMALS
from src.dex.solana.jupiter.executor import execute_swap
from src.utils.log_util import get_dex_logger

logger = get_dex_logger()


def buy(
    symbol: str,
    amount_sol_human: float,
    recipient: Optional[str] = None,
) -> Tuple[Optional[str], bool]:
    """Buy a Solana token with SOL via Jupiter."""
    if recipient is not None:
        logger.warning("Solana buy ignores recipient; swaps execute into the configured wallet")

    ctx = get_swap_context(symbol)
    if not ctx:
        return None, False

    keypair, coin, rpc_url, token_decimals = ctx
    output_address = coin["address"]

    input_lamports = int(round(amount_sol_human * LAMPORTS_PER_SOL))

    try:
        signature, quoted_token_amount = execute_swap(
            rpc_url,
            keypair,
            SOL_ADDRESS,
            output_address,
            input_lamports,
            token_decimals,
            dexes=coin.get("dexes"),
        )
    except Exception as exc:
        logger.error("Solana buy failed for %s: %s", symbol, exc)
        return None, False

    logger.info(
        "Buy Jupiter %s with %s SOL -> %s tokens (tx=%s)",
        symbol,
        amount_sol_human,
        quoted_token_amount,
        signature,
    )
    return signature, True


def sell(
    symbol: str,
    amount_in_human_or_label: Union[float, str],
    recipient: Optional[str] = None,
) -> Tuple[Optional[str], bool]:
    """Sell a Solana token for SOL via Jupiter. Optional ``recipient`` gets the SOL."""
    ctx = get_swap_context(symbol)
    if not ctx:
        return None, False

    keypair, coin, rpc_url, token_decimals = ctx
    input_address = coin["address"]

    amount_raw = resolve_sell_amount_raw(
        rpc_url,
        str(keypair.pubkey()),
        input_address,
        token_decimals,
        amount_in_human_or_label,
    )
    if amount_raw is None or amount_raw <= 0:
        logger.error("Solana sell: invalid amount for %s", symbol)
        return None, False

    try:
        signature, quoted_sol_amount = execute_swap(
            rpc_url,
            keypair,
            input_address,
            SOL_ADDRESS,
            amount_raw,
            SOL_DECIMALS,
            dexes=coin.get("dexes"),
            recipient=recipient,
        )
    except Exception as exc:
        logger.error("Solana sell failed for %s: %s", symbol, exc)
        return None, False

    logger.info(
        "Sell Jupiter %s %s -> ~%s SOL%s (tx=%s)",
        amount_in_human_or_label,
        symbol,
        quoted_sol_amount,
        f" to {recipient}" if recipient else "",
        signature,
    )
    return signature, True
