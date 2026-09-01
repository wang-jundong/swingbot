"""Dual-wallet trade helper (secondary mode, then primary)."""

from __future__ import annotations

from src.storage.settings import set_mode
from src.utils.log_util import get_dex_logger
from src.utils.time_util import local_hour

logger = get_dex_logger()


def execute_dual_mode_trade(action, trade_fn, symbol: str, amount, **kwargs):
    """Trade on secondary wallet (mode 4), then primary, with the same amount."""
    set_mode(local_hour() + 1)
    try:
        _tx_hash, success, *_ = trade_fn(symbol, amount, **kwargs)
        if not success:
            logger.warning("Dual trade failed: %s %s", action, symbol)
    finally:
        set_mode()

    return trade_fn(symbol, amount, **kwargs)
