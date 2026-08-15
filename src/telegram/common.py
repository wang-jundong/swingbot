"""Shared handler helpers."""

from typing import Optional

from telegram.ext import ContextTypes

from src.dex.protocol import DexClient


def parse_callback(data: str, action: str, expected_parts: int) -> Optional[tuple]:
    """Parse callback_data to args tuple."""
    if not data.startswith(action + ":"):
        return None
    parts = data.split(":", expected_parts)
    if len(parts) != expected_parts:
        return None
    return tuple(parts[1:])


def get_dex_client(context: ContextTypes.DEFAULT_TYPE) -> Optional[DexClient]:
    """Get DexClient from bot_data."""
    return context.bot_data.get("dex_client")


def dex_available(context: ContextTypes.DEFAULT_TYPE) -> bool:
    """DEX client available."""
    return get_dex_client(context) is not None
