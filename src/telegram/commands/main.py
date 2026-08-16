"""Main command and keyboard routing."""

import asyncio

from telegram import Update
from telegram.ext import ContextTypes

from src.storage.settings import set_mode
from src.telegram.handlers.history import on_history
from src.telegram.handlers.settings import on_settings
from src.telegram.handlers.trade import prompt_buy, prompt_sell
from src.telegram.ui.keyboards import MAIN_KEYBOARD


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Choose an action:", reply_markup=MAIN_KEYBOARD)


async def on_main_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text or ""
    handlers_map = {
        "Buy": lambda: prompt_buy(update),
        "Sell": lambda: prompt_sell(update),
        "History": lambda: on_history(update, context),
        "Settings": lambda: on_settings(update, context),
    }
    handler = handlers_map.get(text)
    if handler:
        await handler()
