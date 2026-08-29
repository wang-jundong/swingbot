"""Normalize OHLCV rows for the per-mint chart."""

from __future__ import annotations

from src.config.backtest import CANDLE_INTERVAL_SEC
from src.utils.number_util import to_float


def prepare_candles(
    candles: list[dict],
    *,
    now: int | None = None,
    interval_sec: int = CANDLE_INTERVAL_SEC,
) -> dict[str, list]:
    """Sort by time, drop duplicate timestamps, drop the incomplete live bar."""
    rows = []
    for candle in candles or []:
        unix = _unix(candle.get("unix_time") or candle.get("t"))
        if unix is None:
            continue
        rows.append({
            "t": unix,
            "o": to_float(candle.get("open") if "open" in candle else candle.get("o")) or 0.0,
            "h": to_float(candle.get("high") if "high" in candle else candle.get("h")) or 0.0,
            "l": to_float(candle.get("low") if "low" in candle else candle.get("l")) or 0.0,
            "c": to_float(candle.get("close") if "close" in candle else candle.get("c")) or 0.0,
            "v": to_float(candle.get("volume_sol") if "volume_sol" in candle else candle.get("v")) or 0.0,
        })
    rows.sort(key=lambda row: row["t"])
    deduped: dict[int, dict] = {}
    for row in rows:
        deduped[row["t"]] = row
    ordered = [deduped[key] for key in sorted(deduped)]
    if ordered and now is not None and ordered[-1]["t"] + interval_sec > now:
        ordered = ordered[:-1]
    return {
        "t": [row["t"] for row in ordered],
        "o": [row["o"] for row in ordered],
        "h": [row["h"] for row in ordered],
        "l": [row["l"] for row in ordered],
        "c": [row["c"] for row in ordered],
        "v": [row["v"] for row in ordered],
    }


def listing_unix(coin: dict) -> int | None:
    if coin.get("registered_at") is not None:
        return _unix(coin.get("registered_at"))
    buys = coin.get("buy_unix") or []
    age = to_float(coin.get("pair_age"))
    if buys and age is not None:
        return int(min(int(ts) for ts in buys) - age * 86400)
    return _unix(coin.get("time_from"))


def _unix(value) -> int | None:
    number = to_float(value)
    if number is None:
        return None
    return int(number)
