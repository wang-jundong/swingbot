"""Buy/Sell handlers."""

import asyncio

from telegram import Update
from telegram.ext import ContextTypes

from src.config.telegram import (
    BUY_ACTION,
    BUY_AMOUNT_ACTION,
    SELL_ACTION,
    SELL_AMOUNT_ACTION,
)
from src.dex.dual_mode import execute_dual_mode_trade
from src.dex.history.trade_stats import REASON_MANUAL
from src.telegram.common import dex_available, get_dex_client, parse_callback
from src.telegram.ui.formatters import (
    build_trade_select_message,
    format_buy_result,
    format_sell_result,
)
from src.telegram.ui.keyboards import (
    build_buy_amount_keyboard,
    build_buy_keyboard,
    build_sell_amount_keyboard,
    build_sell_keyboard,
)


async def prompt_buy(update: Update) -> None:
    markup = build_buy_keyboard()
    if not markup:
        await update.message.reply_text("No tokens.")
        return
    await update.message.reply_text("Select token to Buy:", reply_markup=markup)


async def prompt_sell(update: Update) -> None:
    markup = build_sell_keyboard()
    if not markup:
        await update.message.reply_text("No tokens.")
        return
    await update.message.reply_text("Select token to Sell:", reply_markup=markup)


async def on_buy_token(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    parsed = parse_callback(query.data, BUY_ACTION, 2)
    if not parsed:
        return
    symbol = parsed[0]
    message_text = build_trade_select_message("🟢", symbol)
    markup = build_buy_amount_keyboard(symbol)
    await query.edit_message_text(
        text=message_text,
        parse_mode="Markdown",
        reply_markup=markup,
    )


async def on_buy_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    parsed = parse_callback(query.data, BUY_AMOUNT_ACTION, 3)
    if not parsed:
        return
    symbol, amount_str = parsed
    try:
        amount = float(amount_str)
    except ValueError:
        await query.edit_message_text(text=f"🟢 BUY {symbol} — error: invalid amount")
        return

    await query.edit_message_text(
        text=f"🟢 **BUY** **{symbol}** — {amount_str} \n_Sending tx…_",
        parse_mode="Markdown",
    )

    if not dex_available(context):
        await query.edit_message_text(
            text="🟢 **BUY** failed — DEX client not initialized. Check server logs.",
            parse_mode="Markdown",
        )
        return

    client = get_dex_client(context)
    try:
        tx_hash, success, balance_before, balance_after = await asyncio.to_thread(
            execute_dual_mode_trade, "buy", client.buy, symbol, amount
        )
        if tx_hash:
            await query.edit_message_text(
                text=format_buy_result(
                    symbol,
                    amount_str,
                    tx_hash,
                    success,
                    balance_before,
                    balance_after,
                ),
                parse_mode="HTML",
            )
        else:
            await query.edit_message_text(
                text=f"🟢 **BUY** **{symbol}** — failed (see logs)",
                parse_mode="Markdown",
            )
    except (ValueError, Exception) as e:
        await query.edit_message_text(text=f"🟢 BUY {symbol} — error: {str(e)[:200]}")


async def on_sell_token(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    parsed = parse_callback(query.data, SELL_ACTION, 2)
    if not parsed:
        return
    symbol = parsed[0]
    message_text = build_trade_select_message("🔴", symbol)
    markup = build_sell_amount_keyboard(symbol)
    await query.edit_message_text(
        text=message_text,
        parse_mode="Markdown",
        reply_markup=markup,
    )


async def on_sell_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    parsed = parse_callback(query.data, SELL_AMOUNT_ACTION, 3)
    if not parsed:
        return
    symbol, amount_label = parsed
    await query.edit_message_text(
        text=f"🔴 **SELL** **{symbol}** — {amount_label}\n_Sending tx…_",
        parse_mode="Markdown",
    )

    if not dex_available(context):
        await query.edit_message_text(
            text="🔴 **SELL** failed — DEX client not initialized. Check server logs.",
            parse_mode="Markdown",
        )
        return

    client = get_dex_client(context)
    reason = REASON_MANUAL
    try:
        tx_hash, success, pnl, balance_before, balance_after = await asyncio.to_thread(
            execute_dual_mode_trade,
            "sell",
            client.sell,
            symbol,
            amount_label,
            reason=reason,
        )
        if tx_hash:
            await query.edit_message_text(
                text=format_sell_result(
                    symbol,
                    amount_label,
                    tx_hash,
                    success,
                    pnl,
                    balance_before,
                    balance_after,
                    reason,
                ),
                parse_mode="HTML",
            )
        else:
            await query.edit_message_text(
                text=f"🔴 **SELL** **{symbol}** — failed (see logs)",
                parse_mode="Markdown",
            )
    except Exception as e:
        await query.edit_message_text(text=f"🔴 SELL {symbol} — error: {str(e)[:200]}")
