"""Cumulative trade statistics, grouped by pending buy count."""

import json
from pathlib import Path
from typing import Optional

from src.config.bindings.paths import TRADE_STATS_PATH
from src.utils.log_util import get_dex_logger
from src.utils.number_util import format_decimal

logger = get_dex_logger()


def _new_bucket() -> dict[str, float | int]:
    return {
        "pnl_positive_count": 0,
        "pnl_negative_count": 0,
        "pnl_positive_sum": 0.0,
        "pnl_negative_sum": 0.0,
        "pnl": 0.0,
    }


def _parse_bucket(bucket: dict) -> dict[str, float | int]:
    return {
        "pnl_positive_count": int(bucket.get("pnl_positive_count", 0)),
        "pnl_negative_count": int(bucket.get("pnl_negative_count", 0)),
        "pnl_positive_sum": float(bucket.get("pnl_positive_sum", 0)),
        "pnl_negative_sum": float(bucket.get("pnl_negative_sum", 0)),
        "pnl": float(bucket.get("pnl", 0)),
    }


def _unwrap_legacy(raw: dict) -> dict:
    """Accept current {buy_count: bucket} or legacy {chain: {buy_count: bucket}}."""
    sample = next(iter(raw.values()), None)
    if isinstance(sample, dict) and "pnl" in sample:
        return raw
    unwrapped: dict = {}
    for by_buy_count in raw.values():
        if not isinstance(by_buy_count, dict):
            continue
        for buy_count, bucket in by_buy_count.items():
            if isinstance(bucket, dict) and "pnl" in bucket:
                unwrapped[str(buy_count)] = bucket
    return unwrapped


def load_trade_stats(
    filepath: Optional[Path | str] = None,
) -> dict[str, dict[str, float | int]]:
    """Load stats: buy_count -> counters and sums."""
    path = Path(filepath or TRADE_STATS_PATH)
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text())
    except Exception:
        return {}
    if not isinstance(raw, dict):
        return {}

    stats: dict[str, dict[str, float | int]] = {}
    for buy_count, bucket in _unwrap_legacy(raw).items():
        if isinstance(bucket, dict):
            stats[str(buy_count)] = _parse_bucket(bucket)
    return stats


def save_trade_stats(
    data: dict[str, dict[str, float | int]],
    filepath: Optional[Path | str] = None,
) -> None:
    """Save stats JSON."""
    path = Path(filepath or TRADE_STATS_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    output = {
        buy_count: {
            "pnl_positive_count": str(int(bucket["pnl_positive_count"])),
            "pnl_negative_count": str(int(bucket["pnl_negative_count"])),
            "pnl_positive_sum": format_decimal(float(bucket["pnl_positive_sum"])),
            "pnl_negative_sum": format_decimal(float(bucket["pnl_negative_sum"])),
            "pnl": format_decimal(float(bucket["pnl"])),
        }
        for buy_count, bucket in sorted(data.items(), key=lambda item: int(item[0]))
    }
    path.write_text(json.dumps(output, indent=2, ensure_ascii=False))


def record_trade_stat(
    pnl: float,
    buy_count: int,
    filepath: Optional[Path | str] = None,
) -> dict[str, float | int]:
    """Add one max sell to the stats for this buy count."""
    path = Path(filepath or TRADE_STATS_PATH)
    stats = load_trade_stats(path)
    bucket = stats.setdefault(str(buy_count), _new_bucket())

    pnl = float(pnl)
    if pnl > 0:
        bucket["pnl_positive_count"] += 1
        bucket["pnl_positive_sum"] += pnl
    elif pnl < 0:
        bucket["pnl_negative_count"] += 1
        bucket["pnl_negative_sum"] += pnl
    bucket["pnl"] += pnl

    save_trade_stats(stats, path)
    logger.info(
        "Trade stats buy_count=%s: pnl=%s total=%s (+/%s -/%s)",
        buy_count,
        format_decimal(pnl),
        format_decimal(float(bucket["pnl"])),
        bucket["pnl_positive_count"],
        bucket["pnl_negative_count"],
    )
    return bucket


def get_trade_stats(
    filepath: Optional[Path | str] = None,
) -> dict[str, dict[str, float | int]]:
    """Return all stats."""
    return load_trade_stats(filepath)
