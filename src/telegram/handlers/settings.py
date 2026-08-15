"""Telegram handlers for swing service settings."""

from telegram import Update
from telegram.ext import ContextTypes

from src.storage.settings import load_settings, toggle_setting
from src.telegram.ui.keyboards import build_settings_keyboard


def _settings_text() -> str:
    s = load_settings()
    bot = "RUNNING ✅" if s["swing_enabled"] else "STOPPED ❌"
    auto_sell = "ON ✅" if s["swing_auto_sell_enabled"] else "OFF ❌"
    return (
        "⚙️ <b>Settings</b>\n\n"
        f"<b>Bot:</b> {bot}\n"
        f"<b>Auto sell:</b> {auto_sell}"
    )


async def _edit_settings(query) -> None:
    await query.edit_message_text(
        _settings_text(),
        parse_mode="HTML",
        reply_markup=build_settings_keyboard(),
    )


async def on_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show settings with inline toggles."""
    await update.message.reply_text(
        _settings_text(),
        parse_mode="HTML",
        reply_markup=build_settings_keyboard(),
    )


async def on_settings_swing_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if toggle_setting("swing") is None:
        await query.answer("Unable to update setting.", show_alert=False)
        return
    await _edit_settings(query)


async def on_settings_swing_auto_sell(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if toggle_setting("swing_auto_sell") is None:
        await query.answer("Unable to update setting.", show_alert=False)
        return
    await _edit_settings(query)
