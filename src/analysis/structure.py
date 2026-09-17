"""Market-structure labels: pivots, HH/HL/LH/LL, and KAMA."""

from __future__ import annotations

from src.config.structure import (
    ATR_PERIOD,
    PIVOT_ATR_MULT,
    KAMA_PIVOT_ATR_MULT,
    KAMA_FAST,
    KAMA_FLAT_ATR,
    KAMA_PERIOD,
    KAMA_SLOPE,
    KAMA_SLOW,
    PIVOT_LEFT,
    PIVOT_RIGHT,
    MIN_BAR_DISTANCE,
    MIN_PRICE_DISTANCE,
)


def analyze_structure(candles: list[dict]) -> dict:
    """Label swing structure on OHLC rows with keys t, o, h, l, c."""
    empty = {
        "pivots": [],
        "kama": [],
        "kama_pivots": [],
        "trend": "neutral",
        "kama_filter": "neutral",
        "last_high": None,
        "last_low": None,
    }
    if len(candles) < PIVOT_LEFT + PIVOT_RIGHT + 2:
        return empty

    atr = _wilder_atr(candles, ATR_PERIOD)
    kama = _kama(candles, KAMA_PERIOD, KAMA_FAST, KAMA_SLOW)
    kama_pivots = _filter_pivots(_detect_kama_pivots(
        candles, kama, PIVOT_LEFT, PIVOT_RIGHT, atr
    ))
    raw = _detect_pivots(candles, PIVOT_LEFT, PIVOT_RIGHT, atr)
    swings = _filter_pivots(raw)
    _classify(swings)

    confirm_at: dict[int, list[dict]] = {}
    for pivot in swings:
        confirm_at.setdefault(pivot["i"], []).append(pivot)

    trend = "neutral"
    last_high = None
    last_low = None

    for i in range(len(candles)):
        for pivot in confirm_at.get(i, []):
            if pivot["kind"] == "high":
                last_high = pivot
            else:
                last_low = pivot
            trend = _trend_after(trend, last_high, last_low)

    last_i = len(candles) - 1
    return {
        "pivots": [_public_pivot(p) for p in swings],
        "kama": [
            {"t": candles[i]["t"], "value": value}
            for i, value in enumerate(kama)
            if value is not None
        ],
        "kama_pivots": [_public_kama_pivot(p) for p in kama_pivots],
        "trend": trend,
        "kama_filter": _kama_filter(candles[last_i]["c"], kama, atr, last_i),
        "last_high": _public_pivot(last_high) if last_high else None,
        "last_low": _public_pivot(last_low) if last_low else None,
    }


def _pivot_atr_sides(is_high: bool, is_low: bool, high: float, low: float,
                     close: float, atr: float | None,
                     multiplier: float | None = None) -> tuple[bool, bool]:
    """Filter each candidate side using reversal at the confirmation close."""
    if multiplier is None:
        multiplier = PIVOT_ATR_MULT
    if multiplier <= 0:
        return is_high, is_low
    if atr is None:
        return False, False
    threshold = atr * multiplier
    return is_high and high - close >= threshold, is_low and close - low >= threshold


def _detect_pivots(candles: list[dict], left: int, right: int,
                   atr: list[float | None] | None = None) -> list[dict]:
    if atr is None:
        atr = _wilder_atr(candles, ATR_PERIOD)
    pivots: list[dict] = []
    for i in range(left + right, len(candles)):
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
        is_high, is_low = _pivot_atr_sides(
            is_high, is_low, high, low, candles[i]["c"], atr[i]
        )
        if not is_high and not is_low:
            continue
        pivots.append({
            "i": i,
            "t": candles[mid]["t"],
            "price": candles[mid]["c"],
            "kind": "both" if is_high and is_low else ("high" if is_high else "low"),
        })
    return pivots


def _resolve_pivot(pivot: dict, last: dict | None) -> dict:
    """Resolve an outside candle against accepted history, without mutating raw data."""
    if pivot["kind"] != "both":
        return pivot
    kind = "low" if last and last["kind"] == "high" else "high"
    return {**pivot, "kind": kind}


def _filter_pivots(raw: list[dict]) -> list[dict]:
    out: list[dict] = []
    for pivot in raw:
        pivot = _resolve_pivot(pivot, out[-1] if out else None)
        if not out:
            out.append(pivot)
            continue
        last = out[-1]
        if pivot["kind"] == last["kind"]:
            if pivot["kind"] == "high" and pivot["price"] >= last["price"]:
                out[-1] = pivot
            elif pivot["kind"] == "low" and pivot["price"] <= last["price"]:
                out[-1] = pivot
            continue
        # Opposite pivots must move in the expected direction.
        move = (
            last["price"] - pivot["price"]
            if pivot["kind"] == "low"
            else pivot["price"] - last["price"]
        )
        if move <= 0:
            continue
        base = abs(last["price"]) or abs(pivot["price"]) or 0.0
        if MIN_PRICE_DISTANCE > 0 and base and (move / base) <= MIN_PRICE_DISTANCE:
            continue
        if pivot["kind"] == "low" and MIN_BAR_DISTANCE > 0 and (pivot["i"] - last["i"]) < MIN_BAR_DISTANCE:
            continue
        out.append(pivot)
    return out


def _classify(pivots: list[dict]) -> None:
    last_high = None
    last_low = None
    for pivot in pivots:
        if pivot["kind"] == "high":
            if last_high is None:
                pivot["label"] = "H"
            else:
                pivot["label"] = "HH" if pivot["price"] > last_high["price"] else "LH"
            last_high = pivot
        else:
            if last_low is None:
                pivot["label"] = "L"
            else:
                pivot["label"] = "HL" if pivot["price"] > last_low["price"] else "LL"
            last_low = pivot


def _trend_after(trend: str, last_high: dict | None, last_low: dict | None) -> str:
    high_label = (last_high or {}).get("label")
    low_label = (last_low or {}).get("label")
    if high_label == "HH" and low_label == "HL":
        return "bullish"
    if high_label == "LH" and low_label == "LL":
        return "bearish"
    return trend


def _wilder_atr(candles: list[dict], period: int) -> list[float | None]:
    trs: list[float] = []
    for i, row in enumerate(candles):
        high, low = row["h"], row["l"]
        if i == 0:
            trs.append(high - low)
            continue
        prev_close = candles[i - 1]["c"]
        trs.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
    atr: list[float | None] = [None] * len(candles)
    if len(trs) < period:
        return atr
    seed = sum(trs[:period]) / period
    atr[period - 1] = seed
    prev = seed
    for i in range(period, len(trs)):
        prev = (prev * (period - 1) + trs[i]) / period
        atr[i] = prev
    return atr


def _kama(candles: list[dict], period: int, fast: int, slow: int) -> list[float | None]:
    closes = [row["c"] for row in candles]
    out: list[float | None] = [None] * len(closes)
    if len(closes) <= period:
        return out
    fast_sc = 2 / (fast + 1)
    slow_sc = 2 / (slow + 1)
    value = closes[period]
    out[period] = value
    for i in range(period + 1, len(closes)):
        change = abs(closes[i] - closes[i - period])
        volatility = 0.0
        for j in range(i - period + 1, i + 1):
            volatility += abs(closes[j] - closes[j - 1])
        er = 0.0 if volatility == 0 else change / volatility
        sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2
        value = value + sc * (closes[i] - value)
        out[i] = value
    return out


def _detect_kama_pivots(
    candles: list[dict],
    kama: list[float | None],
    left: int,
    right: int,
    atr: list[float | None] | None = None,
) -> list[dict]:
    """Return KAMA turns confirmed against the candle close and ATR."""
    if atr is None:
        atr = _wilder_atr(candles, ATR_PERIOD)
    pivots: list[dict] = []
    size = min(len(candles), len(kama))
    for i in range(left + right, size):
        mid = i - right
        value = kama[mid]
        if value is None:
            continue
        is_high = True
        is_low = True
        for j in range(mid - left, mid + right + 1):
            if j == mid:
                continue
            other = kama[j]
            if other is None:
                is_high = False
                is_low = False
                break
            if other > value or (j > mid and other == value):
                is_high = False
            if other < value or (j > mid and other == value):
                is_low = False
            if not is_high and not is_low:
                break
        if not is_high and not is_low:
            continue
        is_high, is_low = _pivot_atr_sides(
            is_high, is_low, value, value, candles[i]["c"], atr[i],
            KAMA_PIVOT_ATR_MULT,
        )
        if not is_high and not is_low:
            continue
        pivots.append({
            "i": i,
            "t": candles[mid]["t"],
            "value": value,
            "price": value,
            "kind": "both" if is_high and is_low else ("high" if is_high else "low"),
        })
    return pivots


def _kama_filter(
    price: float,
    kama: list[float | None],
    atr: list[float | None],
    i: int,
) -> str:
    current = kama[i] if i < len(kama) else None
    prev_i = i - KAMA_SLOPE
    previous = kama[prev_i] if prev_i >= 0 and prev_i < len(kama) else None
    if current is None or previous is None:
        return "neutral"
    noise = 0.0
    for j in range(i, -1, -1):
        if atr[j] is not None:
            noise = atr[j] * KAMA_FLAT_ATR
            break
    delta = current - previous
    if abs(delta) <= noise:
        return "neutral"
    if price > current and delta > 0:
        return "bullish"
    if price < current and delta < 0:
        return "bearish"
    return "neutral"


def _public_pivot(pivot: dict) -> dict:
    return {
        "t": pivot["t"],
        "price": pivot["price"],
        "kind": pivot["kind"],
        "label": pivot.get("label"),
    }


def _public_kama_pivot(pivot: dict) -> dict:
    return {
        "t": pivot["t"],
        "value": pivot["value"],
        "kind": pivot["kind"],
    }
