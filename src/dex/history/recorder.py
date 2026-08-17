"""Record DEX buy/sell transactions after tx success."""

from typing import Union

from src.dex.history.daily_pnl import record_daily_pnl
from src.dex.history.trade_stats import record_trade_stat, resolve_sell_reason
from src.dex.history.transaction import save_transaction, close_symbol_and_calculate_pnl
from src.storage.coins import append_sell_metrics
from src.utils.log_util import get_dex_logger

logger = get_dex_logger()


def record_buy(
    symbol: str,
    amount_native_human: float,
    tx_hash: str,
    price: float = 0.0,
) -> None:
    """Persist buy transaction when tx succeeded."""
    try:
        save_transaction(
            action="buy",
            symbol=symbol,
            amount=amount_native_human,
            price=price,
            tx_hash=tx_hash,
            status="pending",
            pnl=0.0,
        )
    except Exception as e:
        logger.warning("Failed to save transaction: %s", e)


def record_sell(
    symbol: str,
    amount_in_human_or_label: Union[float, str],
    tx_hash: str,
    price: float = 0.0,
    amount_native_human: float = 0.0,
    reason: str | None = None,
) -> float:
    """Persist sell transaction when tx succeeded. Returns pnl."""
    amount_native = amount_native_human
    is_max = str(amount_in_human_or_label).strip().lower() == "max"
    if is_max:
        reason = resolve_sell_reason(symbol, reason)
        pnl, _, _, _buy_count = close_symbol_and_calculate_pnl(symbol, amount_native)
        try:
            record_trade_stat(pnl, reason)
        except Exception as e:
            logger.warning("Failed to record trade stats: %s", e)
        if pnl != 0:
            try:
                record_daily_pnl(pnl)
            except Exception as e:
                logger.warning("Failed to record daily PnL: %s", e)
        try:
            append_sell_metrics(symbol, pnl, reason)
        except Exception as e:
            logger.warning("Failed to save sell metrics: %s", e)
        return pnl

    try:
        save_transaction(
            action="sell",
            symbol=symbol,
            amount=amount_native,
            price=price,
            tx_hash=tx_hash,
            status="pending",
            pnl=0.0,
        )
    except Exception as e:
        logger.warning("Failed to save transaction: %s", e)
    return 0.0
