"""History handler."""

import asyncio

from telegram import Update
from telegram.ext import ContextTypes

from src.config.solana import NATIVE_CURRENCY
from src.dex.history.transaction import get_pending_transactions, pnl_native
from src.telegram.ui.formatters import (
    format_history_row,
    format_token_link,
    format_token_summary,
)
from src.telegram.common import dex_available, get_dex_client
from src.utils.log_util import get_telegram_logger

logger = get_telegram_logger()


async def on_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lines = ["<b>📜 History</b>"]

    if not dex_available(context):
        text = "DEX client not initialized. Cannot fetch prices."
        if update.callback_query:
            await update.callback_query.edit_message_text(text)
        else:
            await update.message.reply_text(text)
        return

    client = get_dex_client(context)
    try:
        by_token = await asyncio.to_thread(get_pending_transactions)
        if not by_token:
            lines.append("<i>No pending transactions</i>")
        else:
            symbols = sorted(by_token.keys())
            price_bal_tasks = [
                asyncio.gather(
                    asyncio.to_thread(client.get_price_native, sym),
                    asyncio.to_thread(client.get_balance, sym),
                )
                for sym in symbols
            ]
            results = await asyncio.gather(*price_bal_tasks, return_exceptions=True)

            for i, symbol in enumerate(symbols):
                rows = by_token[symbol]["rows"]
                net_cost = by_token[symbol]["net_cost"]
                lines.append(f"▸ {format_token_link(symbol)}")

                res = results[i] if i < len(results) else None
                if isinstance(res, BaseException):
                    lines.append("   <i>—</i>")
                else:
                    price, bal = res
                    pnl = pnl_native(price, bal, net_cost)
                    if pnl is not None:
                        lines.extend(
                            format_token_summary(price, bal, pnl, currency=NATIVE_CURRENCY)
                        )
                    else:
                        lines.append("   <i>—</i>")

                for row in rows:
                    lines.append(format_history_row(row, currency=NATIVE_CURRENCY))
    except Exception as e:
        logger.warning("Failed to load pending transactions: %s", e)
        lines.append("")
        lines.append(f"<i>Error: {str(e)[:100]}</i>")

    text = "\n\n".join(lines)
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="HTML")
    else:
        await update.message.reply_text(text, parse_mode="HTML")
