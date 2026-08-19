import pandas as pd
from src.config.telegram import LOCAL_TIMEZONE

# format used in CSV, coins, and logs (Asia/Vladivostok wall clock)
DISPLAY_FMT = "%Y-%m-%d %H:%M:%S"


def unix_now() -> int:
    """Current time as Unix timestamp (int)."""
    return int(pd.Timestamp.now(tz="UTC").timestamp())


def unix_to_str(unix_ts: int) -> str:
    """Convert a Unix timestamp to a LOCAL_TIMEZONE display string."""
    return (
        pd.Timestamp(int(unix_ts), unit="s", tz="UTC")
        .tz_convert(LOCAL_TIMEZONE)
        .strftime(DISPLAY_FMT)
    )


def str_to_unix(value: str | None) -> int | None:
    """Parse a LOCAL_TIMEZONE display timestamp to Unix seconds."""
    if not value:
        return None
    try:
        ts = pd.to_datetime(str(value).strip(), format=DISPLAY_FMT)
        if ts.tzinfo is None:
            ts = ts.tz_localize(LOCAL_TIMEZONE)
        return int(ts.timestamp())
    except (TypeError, ValueError):
        return None


def local_hour() -> int:
    """Current hour (0-23) in LOCAL_TIMEZONE."""
    return pd.Timestamp.now(tz=LOCAL_TIMEZONE).hour


def local_date(unix_ts: int | None = None) -> str:
    """YYYY-MM-DD in LOCAL_TIMEZONE."""
    return unix_to_str(unix_now() if unix_ts is None else unix_ts)[:10]
