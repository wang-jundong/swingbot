"""Causal bar walk of pivots, KAMA filter, and BOS/CHoCH."""

from __future__ import annotations

from src.analysis.structure import (
    _event,
    _pivot_atr_sides,
    _resolve_pivot,
    _kama,
    _kama_filter,
    _public_pivot,
    _trend_after,
    _wilder_atr,
)
from src.config.structure import (
    ATR_PERIOD,
    KAMA_FAST,
    KAMA_PERIOD,
    KAMA_SLOW,
    MIN_BAR_DISTANCE,
    MIN_PRICE_DISTANCE,
    PIVOT_LEFT,
    PIVOT_RIGHT,
)


def walk_bars(candles: list[dict]) -> list[dict]:
    """Return one causal snapshot per bar close. No future candles leak in."""
    if not candles:
        return []

    atr = _wilder_atr(candles, ATR_PERIOD)
    kama = _kama(candles, KAMA_PERIOD, KAMA_FAST, KAMA_SLOW)
    filtered: list[dict] = []
    trend = "neutral"
    last_high = None
    last_low = None
    high_broken = False
    low_broken = False
    snapshots: list[dict] = []

    for i, row in enumerate(candles):
        accepted = _accept_pivot(filtered, _pivot_at(candles, i, atr))
        events: list[dict] = []
        if accepted is not None and accepted["i"] == i:
            if accepted["kind"] == "high":
                last_high = accepted
                high_broken = False
            else:
                last_low = accepted
                low_broken = False
            trend = _trend_after(trend, last_high, last_low)

        bias = _kama_filter(row["c"], kama, atr, i)
        close = row["c"]
        if trend == "bullish":
            if last_high and not high_broken and close > last_high["price"]:
                if bias != "bearish":
                    events.append(_event(row, "BOS", "bull"))
                high_broken = True
            if last_low and not low_broken and close < last_low["price"]:
                events.append(_event(row, "CHoCH", "bear"))
                low_broken = True
                trend = "bearish"
        elif trend == "bearish":
            if last_low and not low_broken and close < last_low["price"]:
                if bias != "bullish":
                    events.append(_event(row, "BOS", "bear"))
                low_broken = True
            if last_high and not high_broken and close > last_high["price"]:
                events.append(_event(row, "CHoCH", "bull"))
                high_broken = True
                trend = "bullish"

        snapshots.append({
            "i": i,
            "t": row["t"],
            "open": row["o"],
            "close": close,
            "events": events,
            "trend": trend,
            "kama_filter": bias,
            "last_high": _public_pivot(last_high) if last_high else None,
            "last_low": _public_pivot(last_low) if last_low else None,
        })

    return snapshots


def _pivot_at(candles: list[dict], i: int,
              atr: list[float | None] | None = None) -> dict | None:
    left, right = PIVOT_LEFT, PIVOT_RIGHT
    if i < left + right:
        return None
    mid = i - right
    high = candles[mid]["h"]
    low = candles[mid]["l"]
    is_high = True
    is_low = True
    for j in range(mid - left, mid + right + 1):
        if j == mid:
            continue
        if candles[j]["h"] > high or (j > mid and candles[j]["h"] == high):
            is_high = False
        if candles[j]["l"] < low or (j > mid and candles[j]["l"] == low):
            is_low = False
        if not is_high and not is_low:
            break
    if atr is None:
        atr = _wilder_atr(candles[:i + 1], ATR_PERIOD)
    is_high, is_low = _pivot_atr_sides(
        is_high, is_low, high, low, candles[i]["c"], atr[i]
    )
    if not is_high and not is_low:
        return None
    return {
        "i": i,
        "t": candles[mid]["t"],
        "price": candles[mid]["c"],
        "kind": "both" if is_high and is_low else ("high" if is_high else "low"),
    }


def _accept_pivot(
    filtered: list[dict],
    pivot: dict | None,
) -> dict | None:
    if pivot is None:
        return None
    pivot = _resolve_pivot(pivot, filtered[-1] if filtered else None)
    if not filtered:
        _label(pivot, None)
        filtered.append(pivot)
        return pivot
    last = filtered[-1]
    if pivot["kind"] == last["kind"]:
        if pivot["kind"] == "high" and pivot["price"] >= last["price"]:
            _label(pivot, _prior_same(filtered[:-1], "high"))
            filtered[-1] = pivot
            return pivot
        if pivot["kind"] == "low" and pivot["price"] <= last["price"]:
            _label(pivot, _prior_same(filtered[:-1], "low"))
            filtered[-1] = pivot
            return pivot
        return None
    # Opposite pivots must move in the expected direction.
    move = (
        last["price"] - pivot["price"]
        if pivot["kind"] == "low"
        else pivot["price"] - last["price"]
    )
    if move <= 0:
        return None
    base = abs(last["price"]) or abs(pivot["price"]) or 0.0
    if MIN_PRICE_DISTANCE > 0 and base and (move / base) <= MIN_PRICE_DISTANCE:
        return None
    if MIN_BAR_DISTANCE > 0 and (pivot["i"] - last["i"]) < MIN_BAR_DISTANCE:
        return None
    _label(pivot, _prior_same(filtered, pivot["kind"]))
    filtered.append(pivot)
    return pivot


def _prior_same(pivots: list[dict], kind: str) -> dict | None:
    for item in reversed(pivots):
        if item["kind"] == kind:
            return item
    return None


def _label(pivot: dict, previous: dict | None) -> None:
    if pivot["kind"] == "high":
        pivot["label"] = "H" if previous is None else ("HH" if pivot["price"] > previous["price"] else "LH")
        return
    pivot["label"] = "L" if previous is None else ("HL" if pivot["price"] > previous["price"] else "LL")
