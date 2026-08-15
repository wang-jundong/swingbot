"""Swap helpers: context, amounts, slippage."""

from __future__ import annotations

from typing import Optional, Union

from solders.keypair import Keypair

from src.config.trading import SELL_AMOUNT_LABELS
from src.storage.coins import get_coin_by_symbol
from src.dex.solana.common.spl import get_token_balance_raw, get_token_decimals, human_to_raw
from src.dex.solana.core.connection import get_rpc_and_keypair
from src.utils.log_util import get_dex_logger

logger = get_dex_logger()


def get_swap_context(symbol: str) -> Optional[tuple[Keypair, dict, str, int]]:
    """(keypair, coin, rpc_url, token_decimals) or None."""
    conn = get_rpc_and_keypair()
    if not conn:
        return None
    rpc_url, keypair = conn

    coin = get_coin_by_symbol(symbol)
    if not coin:
        logger.error("Unknown symbol: %s", symbol)
        return None

    address = coin.get("address")
    if not address:
        logger.error("Solana coin %s is missing address", symbol)
        return None

    decimals = coin.get("decimals")
    if decimals is None:
        try:
            decimals = get_token_decimals(rpc_url, address)
        except Exception as exc:
            logger.error("Failed to fetch decimals for %s: %s", symbol, exc)
            return None
    else:
        decimals = int(decimals)

    return keypair, coin, rpc_url, decimals


def resolve_sell_amount_raw(
    rpc_url: str,
    owner: str,
    address: str,
    decimals: int,
    amount_or_label: Union[float, str],
) -> Optional[int]:
    """Resolve amount_or_label (float or 'max'/'1/2'/'1/3'/'1/4') to raw units."""
    balance_raw = get_token_balance_raw(rpc_url, owner, address)
    if balance_raw <= 0:
        return None

    if isinstance(amount_or_label, str):
        if amount_or_label not in SELL_AMOUNT_LABELS:
            logger.error("Invalid sell amount label: %s", amount_or_label)
            return None
        if amount_or_label == "max":
            return balance_raw
        numerator, denominator = amount_or_label.split("/")
        try:
            num = int(numerator)
            den = int(denominator)
        except ValueError:
            logger.error("Invalid sell amount fraction: %s", amount_or_label)
            return None
        if den <= 0 or num <= 0:
            logger.error("Invalid sell amount fraction: %s", amount_or_label)
            return None
        return balance_raw * num // den

    amount_in = human_to_raw(float(amount_or_label), decimals)
    return min(amount_in, balance_raw) if amount_in > 0 else None
