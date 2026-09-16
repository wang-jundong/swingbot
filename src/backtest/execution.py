"""Next-bar fills with slippage and a flat fee."""

from __future__ import annotations

from src.config.backtest import BUY_SLIPPAGE, FEE_SOL, POSITION_SIZE_SOL, SELL_SLIPPAGE


def buy_fill(bar: dict, sol_in: float = POSITION_SIZE_SOL) -> dict | None:
    price = _px(bar.get("o"))
    if price is None or price <= 0 or sol_in <= 0:
        return None
    fill = price * (1.0 + BUY_SLIPPAGE)
    tokens = sol_in / fill
    if tokens <= 0:
        return None
    return {
        "t": bar["t"],
        "price": fill,
        "tokens": tokens,
        "sol": sol_in + FEE_SOL,
        "fee": FEE_SOL,
    }


def sell_fill(bar: dict, tokens: float) -> dict | None:
    price = _px(bar.get("o"))
    if price is None or price <= 0 or tokens <= 0:
        return None
    fill = price * (1.0 - SELL_SLIPPAGE)
    if fill <= 0:
        return None
    gross = tokens * fill
    return {
        "t": bar["t"],
        "price": fill,
        "tokens": tokens,
        "sol": max(0.0, gross - FEE_SOL),
        "fee": FEE_SOL,
    }


def close_fill(bar: dict, tokens: float) -> dict | None:
    price = _px(bar.get("c"))
    if price is None or price <= 0 or tokens <= 0:
        return None
    fill = price * (1.0 - SELL_SLIPPAGE)
    if fill <= 0:
        return None
    gross = tokens * fill
    return {
        "t": bar["t"],
        "price": fill,
        "tokens": tokens,
        "sol": max(0.0, gross - FEE_SOL),
        "fee": FEE_SOL,
    }


def _px(value: object) -> float | None:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if number == number else None
