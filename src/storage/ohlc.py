"""Read exported Birdeye OHLCV files under var/ohlc/<wallet>/<mint>.json."""

from __future__ import annotations

import json
import re
import threading
from collections import OrderedDict
from pathlib import Path

from src.config.bindings.binding import BINDINGS
from src.config.bindings.paths import OHLC_PATH
from src.utils.number_util import to_float

_SAFE_ID = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")
_INDEX_LOCK = threading.Lock()
_CURVE_LOCK = threading.Lock()
_INDEX_CACHE: tuple[tuple, list[dict]] | None = None
_CURVE_CACHE: OrderedDict[tuple[str, float], list[dict]] = OrderedDict()
_CURVE_CACHE_MAX = 4
_MAX_BARS = 8000
INTERVALS = {
    "15s": 15,
    "30s": 30,
    "1m": 60,
    "5m": 300,
    "15m": 900,
}


def ohlc_root() -> Path:
    return Path(OHLC_PATH)


def safe_id(value: str | None) -> str | None:
    text = str(value or "").strip()
    return text if text and _SAFE_ID.fullmatch(text) else None


def default_wallet() -> str | None:
    wallet = safe_id(BINDINGS.get("SOLANA_PUBLIC_ADDRESS"))
    if wallet and (ohlc_root() / wallet).is_dir():
        return wallet
    return None


def list_wallets() -> list[str]:
    root = ohlc_root()
    if not root.is_dir():
        return []
    return sorted(path.name for path in root.iterdir() if path.is_dir() and safe_id(path.name))


def list_ohlc_tokens(wallet: str | None = None) -> list[dict]:
    wanted = safe_id(wallet)
    tokens = _index()
    if wanted:
        tokens = [token for token in tokens if wanted in token["wallets"]]
        for token in tokens:
            token["wallet"] = wanted if wanted in token["wallets"] else token["wallet"]
    return tokens


def ohlc_curve(
    address: str,
    wallet: str | None = None,
    interval: str = "1m",
    time_from: int | None = None,
    time_to: int | None = None,
) -> dict | None:
    mint = safe_id(address)
    if not mint:
        return None
    token = _find_token(mint, safe_id(wallet))
    if token is None:
        return None
    path = Path(token["path"])
    candles = _load_candles(path)
    key = interval if interval in INTERVALS else "1m"
    step = INTERVALS[key]
    empty = {
        "address": mint,
        "wallet": token["wallet"],
        "interval": key,
        "source": token.get("source") or "birdeye",
        "creation_time": token.get("creation_time"),
        "exported_at": token.get("exported_at"),
        "time_from": None,
        "time_to": None,
        "full_from": None,
        "full_to": None,
        "points": [],
    }
    if not candles:
        return empty

    full_from = candles[0]["t"]
    full_to = candles[-1]["t"]
    start = int(time_from) if time_from else None
    end = int(time_to) if time_to else None
    selected = candles
    if start is not None and end is not None and end > start:
        selected = [row for row in candles if start <= row["t"] <= end]
    points = _aggregate(selected, step)
    if start is None and len(points) > _MAX_BARS:
        points = points[-_MAX_BARS:]
    return {
        "address": mint,
        "wallet": token["wallet"],
        "interval": key,
        "source": token.get("source") or "birdeye",
        "creation_time": token.get("creation_time"),
        "exported_at": token.get("exported_at"),
        "time_from": points[0]["t"] if points else None,
        "time_to": points[-1]["t"] if points else None,
        "full_from": full_from,
        "full_to": full_to,
        "first": selected[0]["c"] if selected else None,
        "last": selected[-1]["c"] if selected else None,
        "high": max(row["h"] for row in selected) if selected else None,
        "low": min(row["l"] for row in selected) if selected else None,
        "points": points,
    }


def _index() -> list[dict]:
    global _INDEX_CACHE
    root = ohlc_root()
    stamp = _root_stamp(root)
    with _INDEX_LOCK:
        if _INDEX_CACHE and _INDEX_CACHE[0] == stamp:
            return [dict(token) for token in _INDEX_CACHE[1]]
        rows: dict[str, dict] = {}
        for wallet in list_wallets():
            folder = root / wallet
            for path in folder.glob("*.json"):
                mint = safe_id(path.stem)
                if mint is None:
                    continue
                meta = _read_meta(path, mint, wallet)
                current = rows.get(mint)
                if current is None or _prefer(meta, current):
                    if current is not None:
                        meta["wallets"] = sorted(set(current["wallets"]) | {wallet})
                    rows[mint] = meta
                else:
                    current["wallets"] = sorted(set(current["wallets"]) | {wallet})
        tokens = sorted(rows.values(), key=lambda row: row.get("time_to") or 0, reverse=True)
        _INDEX_CACHE = (stamp, tokens)
        return [dict(token) for token in tokens]


def _find_token(mint: str, wallet: str | None) -> dict | None:
    for token in _index():
        if token["address"] != mint:
            continue
        if wallet and wallet not in token["wallets"]:
            continue
        if wallet:
            token = dict(token)
            token["wallet"] = wallet
            token["path"] = str(ohlc_root() / wallet / f"{mint}.json")
        return token
    return None


def _prefer(candidate: dict, current: dict) -> bool:
    default = default_wallet()
    if default:
        if candidate["wallet"] == default and current["wallet"] != default:
            return True
        if current["wallet"] == default and candidate["wallet"] != default:
            return False
    return (candidate.get("candle_count") or 0) > (current.get("candle_count") or 0)


def _root_stamp(root: Path) -> tuple:
    if not root.is_dir():
        return ()
    parts = []
    for folder in sorted(root.iterdir()):
        if folder.is_dir():
            stat = folder.stat()
            parts.append((folder.name, stat.st_mtime_ns, stat.st_size))
    return tuple(parts)


def _read_meta(path: Path, mint: str, wallet: str) -> dict:
    head = _read_head(path, 4000)
    tail = _read_tail(path, 2500)
    first = _first_candle(head)
    last = _last_candle(tail)
    first_close = to_float((first or {}).get("c"))
    last_close = to_float((last or {}).get("c"))
    change_pct = None
    if first_close not in (None, 0) and last_close is not None:
        change_pct = (last_close - first_close) / first_close * 100
    return {
        "address": mint,
        "wallet": wallet,
        "wallets": [wallet],
        "path": str(path),
        "source": _text_field(head, "source"),
        "interval": _text_field(head, "interval") or "1m",
        "creation_time": _int_field(head, "creation_time"),
        "age_seconds": _int_field(head, "age_seconds"),
        "time_from": _int_field(head, "time_from"),
        "time_to": _int_field(head, "time_to"),
        "candle_count": _int_field(head, "candle_count"),
        "exported_at": _text_field(head, "exported_at"),
        "first": first_close,
        "last": last_close,
        "change_pct": None if change_pct is None else round(change_pct, 4),
        "size": path.stat().st_size,
    }


def _read_head(path: Path, n: int) -> str:
    with path.open("r", encoding="utf-8") as handle:
        return handle.read(n)


def _read_tail(path: Path, n: int) -> str:
    size = path.stat().st_size
    with path.open("rb") as handle:
        handle.seek(max(0, size - n))
        return handle.read().decode("utf-8", errors="ignore")


def _text_field(text: str, key: str) -> str | None:
    match = re.search(rf'"{re.escape(key)}"\s*:\s*"([^"]*)"', text)
    return match.group(1) if match else None


def _int_field(text: str, key: str) -> int | None:
    match = re.search(rf'"{re.escape(key)}"\s*:\s*(-?\d+)', text)
    return int(match.group(1)) if match else None


def _first_candle(head: str) -> dict | None:
    match = re.search(r'"candles"\s*:\s*\[\s*(\{.*?\})', head, re.S)
    return _parse_candle_blob(match.group(1)) if match else None


def _last_candle(tail: str) -> dict | None:
    matches = list(re.finditer(r'\{\s*"t"\s*:\s*-?\d+[\s\S]*?\}', tail))
    for match in reversed(matches):
        parsed = _parse_candle_blob(match.group(0))
        if parsed and parsed.get("c") is not None:
            return parsed
    return None


def _parse_candle_blob(blob: str) -> dict | None:
    try:
        data = json.loads(blob)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _load_candles(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    stamp = (str(path), path.stat().st_mtime)
    with _CURVE_LOCK:
        cached = _CURVE_CACHE.get(stamp)
        if cached is not None:
            _CURVE_CACHE.move_to_end(stamp)
            return cached
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    raw = data.get("candles") if isinstance(data, dict) else None
    candles = []
    for row in raw or []:
        if not isinstance(row, dict):
            continue
        t = to_float(row.get("t"))
        close = to_float(row.get("c"))
        if t is None or close is None:
            continue
        high = to_float(row.get("h"))
        low = to_float(row.get("l"))
        candles.append({
            "t": int(t),
            "o": to_float(row.get("o")) if to_float(row.get("o")) is not None else close,
            "h": high if high is not None else close,
            "l": low if low is not None else close,
            "c": close,
            "v": to_float(row.get("v")) or 0.0,
            "v_usd": to_float(row.get("v_usd")) or 0.0,
        })
    candles.sort(key=lambda row: row["t"])
    with _CURVE_LOCK:
        _CURVE_CACHE[stamp] = candles
        _CURVE_CACHE.move_to_end(stamp)
        while len(_CURVE_CACHE) > _CURVE_CACHE_MAX:
            _CURVE_CACHE.popitem(last=False)
    return candles


def _aggregate(candles: list[dict], step_sec: int) -> list[dict]:
    if step_sec <= 60:
        return [_compact(row) for row in candles]
    buckets: list[dict] = []
    current: dict | None = None
    for row in candles:
        bucket_t = row["t"] - (row["t"] % step_sec)
        if current is None or current["t"] != bucket_t:
            if current is not None:
                buckets.append(_compact(current))
            current = {
                "t": bucket_t,
                "o": row["o"],
                "h": row["h"],
                "l": row["l"],
                "c": row["c"],
                "v": row["v"],
                "v_usd": row["v_usd"],
            }
            continue
        current["h"] = max(current["h"], row["h"])
        current["l"] = min(current["l"], row["l"])
        current["c"] = row["c"]
        current["v"] += row["v"]
        current["v_usd"] += row["v_usd"]
    if current is not None:
        buckets.append(_compact(current))
    return buckets


def _compact(row: dict) -> dict:
    return {
        "t": int(row["t"]),
        "o": _px(row["o"]),
        "h": _px(row["h"]),
        "l": _px(row["l"]),
        "c": _px(row["c"]),
        "v": _px(row["v"]),
        "v_usd": _px(row.get("v_usd") or 0),
    }


def _px(value: float | None) -> float | None:
    number = to_float(value)
    if number is None:
        return None
    return float(f"{number:.10g}")
