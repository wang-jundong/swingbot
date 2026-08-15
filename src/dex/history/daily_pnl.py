"""Daily realized PnL (JSON)."""

import json
from pathlib import Path
from typing import Optional

from src.config.bindings.paths import DAILY_PNL_PATHS
from src.storage.settings import get_key_id
from src.utils.log_util import get_dex_logger
from src.utils.number_util import format_decimal
from src.utils.time_util import unix_now, unix_to_str

logger = get_dex_logger()


def _pnl_path(filepath: Optional[Path | str] = None) -> Path:
    if filepath:
        return Path(filepath)
    key_id = get_key_id()
    return Path(DAILY_PNL_PATHS.get(key_id, DAILY_PNL_PATHS["solana"]))


def _day_pnl(value) -> float:
    if isinstance(value, dict):
        if "sol" in value:
            return float(value.get("sol") or 0)
        return float(next(iter(value.values()), 0) or 0)
    return float(value or 0)


def date_key(unix_ts: Optional[int] = None) -> str:
    """YYYY-MM-DD"""
    return unix_to_str(unix_ts if unix_ts is not None else unix_now())[:10]


def load_daily_pnl(filepath: Optional[Path | str] = None) -> dict[str, float]:
    """Load daily PnL JSON keyed by date."""
    path = _pnl_path(filepath)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        return {str(day): _day_pnl(value) for day, value in data.items()}
    except Exception:
        return {}


def save_daily_pnl(
    data: dict[str, float],
    filepath: Optional[Path | str] = None,
) -> None:
    """Save daily PnL JSON."""
    path = _pnl_path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = {
        day: format_decimal(float(value))
        for day, value in sorted(data.items())
    }
    path.write_text(json.dumps(normalized, indent=2, ensure_ascii=False))


def record_daily_pnl(
    pnl: float,
    filepath: Optional[Path | str] = None,
    unix_ts: Optional[int] = None,
) -> float:
    """Add PnL to today. Returns that day's total."""
    path = _pnl_path(filepath)
    day = date_key(unix_ts)
    data = load_daily_pnl(path)
    data[day] = data.get(day, 0.0) + float(pnl)
    save_daily_pnl(data, path)
    logger.info("Daily PnL %s: %s", day, format_decimal(data[day]))
    return data[day]
