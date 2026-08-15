"""Message formatters."""

from typing import Optional

from src.config.solana import DEXSCREENER_EXPLORER, NATIVE_CURRENCY, TX_EXPLORER
from src.storage.coins import get_coin_by_symbol
from src.utils.number_util import format_decimal


def format_token_summary(
    price: Optional[float],
    balance: Optional[float],
    pnl_native: Optional[float] = None,
    *,
    currency: str = "SOL",
) -> list[str]:
    """Format price, value, PnL."""
    if price is None or balance is None or price <= 0:
        return []
    value_native = price * balance
    lines = [
        f"   Price: <code>{format_decimal(price)}</code> {currency}",
        f"   Value: <code>{format_decimal(value_native)}</code> {currency}",
    ]
    if pnl_native is not None:
        pnl_emoji = "📈" if pnl_native >= 0 else "📉"
        sign = "+" if pnl_native >= 0 else ""
        lines.append(
            f"   PnL: {pnl_emoji} <code>{sign}{format_decimal(pnl_native)}</code> {currency}"
        )
    return lines


def format_token_link(symbol: str) -> str:
    """Bold token name, with Dexscreener link when address is known."""
    coin = get_coin_by_symbol(symbol)
    address = coin.get("address") if coin else None
    if address:
        return f"<a href='{DEXSCREENER_EXPLORER.format(address)}'><b>{symbol}</b></a>"
    return f"<b>{symbol}</b>"


def build_trade_select_message(side: str, symbol: str) -> str:
    """Token selection message (Markdown)."""
    header = f"{side} You selected **{'BUY' if side == '🟢' else 'SELL'}** for **{symbol}**."
    return f"{header}\nChoose amount:"


def format_buy_result(
    symbol: str,
    amount,
    tx_hash: str,
    success: bool,
    balance_before: Optional[float] = None,
    balance_after: Optional[float] = None,
) -> str:
    """Buy result message (HTML)."""
    suffix = "✅" if success else "❌"
    lines = [
        f"🟢 <b>BUY</b> <b>{symbol}</b> — {amount}",
        f"<a href='{TX_EXPLORER.format(tx_hash)}'>{suffix} Open Transaction</a>",
    ]
    if success and balance_before is not None and balance_after is not None:
        lines.extend(
            [
                "",
                f"{NATIVE_CURRENCY}: {format_decimal(balance_before)} → {format_decimal(balance_after)}",
            ]
        )
    return "\n".join(lines)


def format_sell_result(
    symbol: str,
    amount,
    tx_hash: str,
    success: bool,
    pnl: float = 0.0,
    balance_before: Optional[float] = None,
    balance_after: Optional[float] = None,
) -> str:
    """Sell result message (HTML)."""
    suffix = "✅" if success else "❌"
    lines = [
        f"🔴 <b>SELL</b> <b>{symbol}</b> — {amount}",
        f"<a href='{TX_EXPLORER.format(tx_hash)}'>{suffix} Open Transaction</a>",
    ]
    if success:
        if balance_before is not None and balance_after is not None:
            lines.extend(
                [
                    "",
                    f"{NATIVE_CURRENCY}: {format_decimal(balance_before)} → {format_decimal(balance_after)}",
                ]
            )
        if pnl != 0:
            lines.append(f"PnL: {format_decimal(pnl)} {NATIVE_CURRENCY}")
    return "\n".join(lines)


def format_sell_alert(symbol: str, balance: float, pnl: float) -> str:
    """Sell-target alert when auto-sell is off (HTML)."""
    return (
        f"🔴 SELL {symbol} — target hit\n"
        f"Balance: {format_decimal(balance)}\n"
        f"PnL: {format_decimal(pnl)} {NATIVE_CURRENCY}"
    )


def format_history_row(row: dict, *, currency: str = "SOL") -> str:
    """Format history row."""
    action = row.get("action", "")
    amt = row.get("amount", "0")
    pr = row.get("price", "0")
    emoji = "🟢" if action == "buy" else "🔴"
    return (
        f"   {emoji} <b>{action}</b> <code>{format_decimal(amt)}</code> {currency} "
        f"@ <code>{format_decimal(pr)}</code> {currency}"
    )
