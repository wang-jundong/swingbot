"""Inactive backtest strategy; no entry or exit signals are generated."""

from __future__ import annotations


def buy_reason(snapshot: dict, buys: int, max_buys: int, has_position: bool) -> str | None:
    """No buy strategy is configured."""
    return None


def sell_reason(
    snapshot: dict,
    position,
    flatten_eot: bool,
    last_bar: bool,
) -> str | None:
    """No sell strategy is configured; final accounting belongs to the runner."""
    return None
