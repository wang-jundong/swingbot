"""Formatted Telegram notification messages."""

from src.telegram.transport import send_message
from src.telegram.ui.formatters import format_buy_result, format_sell_alert, format_sell_result


def send_error(text: str) -> bool:
    """Send an error notification (HTML)."""
    return send_message(text, parse_mode="HTML")


def send_buy(
    symbol: str,
    amount,
    tx_hash: str,
    success: bool,
    balance_before: float | None = None,
    balance_after: float | None = None,
) -> bool:
    """Send a buy result notification (HTML)."""
    return send_message(
        format_buy_result(
            symbol,
            amount,
            tx_hash,
            success,
            balance_before,
            balance_after,
        ),
        parse_mode="HTML",
    )


def send_sell(
    symbol: str,
    amount,
    tx_hash: str,
    success: bool,
    pnl: float = 0.0,
    balance_before: float | None = None,
    balance_after: float | None = None,
    reason: str = "pnl target",
) -> bool:
    """Send a sell result notification (HTML)."""
    return send_message(
        format_sell_result(
            symbol,
            amount,
            tx_hash,
            success,
            pnl,
            balance_before,
            balance_after,
            reason,
        ),
        parse_mode="HTML",
    )


def send_sell_alert(
    symbol: str, balance: float, pnl: float, reason: str = "pnl target",
) -> bool:
    """Send a sell-target or hold-period alert when auto-sell is off (HTML)."""
    return send_message(
        format_sell_alert(symbol, balance, pnl, reason),
        parse_mode="HTML",
    )
