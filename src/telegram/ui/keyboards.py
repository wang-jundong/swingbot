"""Keyboard builders."""

from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from src.config.telegram import (
    BUY_ACTION,
    BUY_AMOUNT_ACTION,
    SELL_ACTION,
    SELL_AMOUNT_ACTION,
    SETTINGS_SWING_AUTO_SELL_ACTION,
    SETTINGS_SWING_TOGGLE_ACTION,
)
from src.config.trading import (
    BUY_AMOUNT_OPTIONS,
    SELL_AMOUNT_LABELS,
)
from src.storage.settings import load_settings
from src.storage.coins import get_all_tokens


MAIN_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("Buy"), KeyboardButton("Sell")],
        [KeyboardButton("History"), KeyboardButton("Settings")],
    ],
    resize_keyboard=True,
    one_time_keyboard=False,
    is_persistent=True,
)


def _pair_row_buttons(buttons: list[InlineKeyboardButton]) -> list[list[InlineKeyboardButton]]:
    """Lay out inline buttons two per row."""
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for button in buttons:
        row.append(button)
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return rows


def _token_keyboard(emoji: str, action: str) -> Optional[InlineKeyboardMarkup]:
    """Tokens, two per row."""
    tokens = get_all_tokens()
    if not tokens:
        return None
    buttons = [
        InlineKeyboardButton(f"{emoji} {c['symbol']}", callback_data=f"{action}:{c['symbol']}")
        for c in tokens
        if c.get("symbol")
    ]
    return InlineKeyboardMarkup(_pair_row_buttons(buttons))


def _amount_keyboard(symbol: str, emoji: str, action: str, options: list) -> InlineKeyboardMarkup:
    """Amount selection buttons."""
    rows = [
        [InlineKeyboardButton(f"{emoji} {opt}", callback_data=f"{action}:{symbol}:{opt}")]
        for opt in options
    ]
    return InlineKeyboardMarkup(rows)


def build_buy_keyboard() -> Optional[InlineKeyboardMarkup]:
    return _token_keyboard("🟢", BUY_ACTION)


def build_sell_keyboard() -> Optional[InlineKeyboardMarkup]:
    return _token_keyboard("🔴", SELL_ACTION)


def build_buy_amount_keyboard(symbol: str) -> InlineKeyboardMarkup:
    return _amount_keyboard(symbol, "🟢", BUY_AMOUNT_ACTION, BUY_AMOUNT_OPTIONS)


def build_sell_amount_keyboard(symbol: str) -> InlineKeyboardMarkup:
    return _amount_keyboard(symbol, "🔴", SELL_AMOUNT_ACTION, list(SELL_AMOUNT_LABELS))


def _on_off_label(enabled: bool) -> str:
    return "ON ✅" if enabled else "OFF ❌"


def _running_label(enabled: bool) -> str:
    return "RUNNING ✅" if enabled else "STOPPED ❌"


def build_settings_keyboard() -> InlineKeyboardMarkup:
    """Settings: swing bot and auto sell."""
    s = load_settings()
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                f"Bot: {_running_label(s['swing_enabled'])}",
                callback_data=SETTINGS_SWING_TOGGLE_ACTION,
            ),
        ],
        [
            InlineKeyboardButton(
                f"Auto sell: {_on_off_label(s['swing_auto_sell_enabled'])}",
                callback_data=SETTINGS_SWING_AUTO_SELL_ACTION,
            ),
        ],
    ])
