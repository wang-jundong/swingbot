import pandas as pd
from src.config.telegram import LOCAL_TIMEZONE

# format used in CSV and logs
DISPLAY_FMT = "%Y-%m-%d %H:%M:%S"


def unix_now() -> int:
    """Current time as Unix timestamp (int)."""
    return int(pd.Timestamp.now().timestamp())


def unix_to_str(unix_ts: int) -> str:
    """Convert a single Unix timestamp to string."""
    return pd.Timestamp(unix_ts, unit="s").strftime(DISPLAY_FMT)


def local_hour() -> int:
    """Current hour (0-23) in LOCAL_TIMEZONE."""
    return pd.Timestamp.now(tz=LOCAL_TIMEZONE).hour
