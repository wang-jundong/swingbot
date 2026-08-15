"""Cumulative trade statistics for target and hold-period exits."""

import json
from pathlib import Path
from typing import Optional

from src.config.bindings.paths import TRADE_STATS_PATH
from src.utils.log_util import get_dex_logger
from src.utils.number_util import format_decimal

logger = get_dex_logger()

REASON_TARGET = "target"
REASON_HOLD = "hold"


def _new_stats() -> dict[str, float | int]:
    return {
        "target_buy_count": 0,
        "target_buy_pnl": 0.0,
        "hold_pnl_positive_count": 0,
        "hold_pnl_positive_sum": 0.0,
        "hold_pnl_negative_count": 0,
        "hold_pnl_negative_sum": 0.0,
        "pnl": 0.0,
    }


def _parse_stats(raw: dict) -> dict[str, float | int]:
    stats = _new_stats()
    stats["target_buy_count"] = int(raw.get("target_buy_count", 0))
    stats["target_buy_pnl"] = float(raw.get("target_buy_pnl", 0))
    stats["hold_pnl_positive_count"] = int(raw.get("hold_pnl_positive_count", 0))
    stats["hold_pnl_positive_sum"] = float(raw.get("hold_pnl_positive_sum", 0))
    stats["hold_pnl_negative_count"] = int(raw.get("hold_pnl_negative_count", 0))
    stats["hold_pnl_negative_sum"] = float(raw.get("hold_pnl_negative_sum", 0))
    stats["pnl"] = float(raw.get("pnl", 0))
    return stats


def load_trade_stats(
    filepath: Optional[Path | str] = None,
) -> dict[str, float | int]:
    """Load flat target/hold trade stats."""
    path = Path(filepath or TRADE_STATS_PATH)
    if not path.exists():
        return _new_stats()
    try:
        raw = json.loads(path.read_text())
    except Exception:
        return _new_stats()
    if not isinstance(raw, dict):
        return _new_stats()
    if "target_buy_count" not in raw and "pnl" not in raw:
        return _new_stats()
    # Ignore legacy buy_count-bucket format.
    if any(key.isdigit() for key in raw):
        return _new_stats()
    return _parse_stats(raw)


def save_trade_stats(
    data: dict[str, float | int],
    filepath: Optional[Path | str] = None,
) -> None:
    """Save stats JSON."""
    path = Path(filepath or TRADE_STATS_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "target_buy_count": str(int(data["target_buy_count"])),
        "target_buy_pnl": format_decimal(float(data["target_buy_pnl"])),
        "hold_pnl_positive_count": str(int(data["hold_pnl_positive_count"])),
        "hold_pnl_positive_sum": format_decimal(float(data["hold_pnl_positive_sum"])),
        "hold_pnl_negative_count": str(int(data["hold_pnl_negative_count"])),
        "hold_pnl_negative_sum": format_decimal(float(data["hold_pnl_negative_sum"])),
        "pnl": format_decimal(float(data["pnl"])),
    }
    path.write_text(json.dumps(output, indent=2, ensure_ascii=False))


def record_trade_stat(
    pnl: float,
    reason: str,
    filepath: Optional[Path | str] = None,
) -> dict[str, float | int]:
    """Add one max sell to target or hold stats."""
    path = Path(filepath or TRADE_STATS_PATH)
    stats = load_trade_stats(path)
    pnl = float(pnl)
    reason = str(reason or "").strip().lower()

    if reason == REASON_TARGET:
        stats["target_buy_count"] += 1
        stats["target_buy_pnl"] += pnl
    elif reason == REASON_HOLD:
        if pnl > 0:
            stats["hold_pnl_positive_count"] += 1
            stats["hold_pnl_positive_sum"] += pnl
        elif pnl < 0:
            stats["hold_pnl_negative_count"] += 1
            stats["hold_pnl_negative_sum"] += pnl
    else:
        logger.info("skip trade stats: unknown reason=%s", reason)
        return stats

    stats["pnl"] += pnl
    save_trade_stats(stats, path)
    logger.info(
        "trade stats %s pnl=%s total=%s target=%s/%s hold+=%s/%s hold-=%s/%s",
        reason,
        format_decimal(pnl),
        format_decimal(float(stats["pnl"])),
        stats["target_buy_count"],
        format_decimal(float(stats["target_buy_pnl"])),
        stats["hold_pnl_positive_count"],
        format_decimal(float(stats["hold_pnl_positive_sum"])),
        stats["hold_pnl_negative_count"],
        format_decimal(float(stats["hold_pnl_negative_sum"])),
    )
    return stats


def get_trade_stats(
    filepath: Optional[Path | str] = None,
) -> dict[str, float | int]:
    """Return all stats."""
    return load_trade_stats(filepath)
