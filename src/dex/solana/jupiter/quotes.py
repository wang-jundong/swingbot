"""Jupiter swap quotes."""

from __future__ import annotations

from typing import Optional

from src.dex.solana.common.spl import raw_to_ui
from src.dex.solana.jupiter.api import build_swap
from src.utils.log_util import get_dex_logger

logger = get_dex_logger()


def quote_out_amount(
    taker: str,
    input_address: str,
    output_address: str,
    input_amount: int,
    output_decimals: int,
    dexes: Optional[str] = None,
) -> Optional[float]:
    """Return quoted output amount in human units."""
    if input_amount <= 0:
        return None
    try:
        build = build_swap(
            taker,
            input_address,
            output_address,
            input_amount,
            dexes=dexes,
        )
        return raw_to_ui(build.get("outAmount", "0"), output_decimals)
    except Exception as exc:
        logger.error("Jupiter quote failed: %s", exc)
        return None
