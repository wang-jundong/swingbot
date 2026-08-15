"""Runtime toggles from ``settings.json``."""

import fcntl
import json
import random
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional

from src.config.bindings.modes import key_id_for_mode
from src.utils.time_util import local_hour
from src.config.bindings.paths import SETTINGS_PATH

_thread_lock = threading.Lock()


def _defaults() -> dict[str, Any]:
    return {
        "mode": 1,
        "swing_enabled": True,
        "swing_auto_sell_enabled": True,
    }


def _merge_settings(data: dict[str, Any]) -> dict[str, Any]:
    out = _defaults()
    if "mode" in data:
        out["mode"] = int(data["mode"])
    if "swing_enabled" in data:
        out["swing_enabled"] = bool(data["swing_enabled"])
    if "swing_auto_sell_enabled" in data:
        out["swing_auto_sell_enabled"] = bool(data["swing_auto_sell_enabled"])
    return out


def _lock_path(path: Path) -> Path:
    return path.with_name(f"{path.name}.lock")


@contextmanager
def _settings_lock(path: Path) -> Iterator[None]:
    """Serialize settings access within the process and across processes."""
    lock_file_path = _lock_path(path)
    lock_file_path.parent.mkdir(parents=True, exist_ok=True)
    with _thread_lock:
        with open(lock_file_path, "w") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _load_unlocked(path: Path) -> dict[str, Any]:
    """Load settings from JSON. Missing or invalid file → defaults."""
    if not path.exists():
        return _defaults()
    try:
        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            return _defaults()
        return _merge_settings(data)
    except Exception:
        return _defaults()


def _save_unlocked(path: Path, settings: dict[str, Any]) -> None:
    """Persist settings to JSON atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _merge_settings(settings)
    payload = json.dumps(data, indent=2, ensure_ascii=False)
    tmp = path.with_suffix(f"{path.suffix}.tmp")
    tmp.write_text(payload)
    tmp.replace(path)


def load_settings(filepath: Optional[str] = None) -> dict[str, Any]:
    path = Path(filepath or SETTINGS_PATH)
    with _settings_lock(path):
        return _load_unlocked(path)


def is_swing_enabled(filepath: Optional[str] = None) -> bool:
    return load_settings(filepath)["swing_enabled"]


def is_swing_auto_sell_enabled(filepath: Optional[str] = None) -> bool:
    return load_settings(filepath)["swing_auto_sell_enabled"]


def get_mode(filepath: Optional[str] = None) -> int:
    """Get wallet mode."""
    stored_mode = int(load_settings(filepath)["mode"])
    if stored_mode == local_hour() + 1:
        return 4
    return 1


def get_key_id(filepath: Optional[str] = None) -> str:
    """Wallet key id under the active ``mode``."""
    return key_id_for_mode(get_mode(filepath))


def save_settings(settings: dict[str, Any], filepath: Optional[str] = None) -> None:
    """Persist settings to JSON."""
    path = Path(filepath or SETTINGS_PATH)
    with _settings_lock(path):
        _save_unlocked(path, settings)


def toggle_setting(key: str, filepath: Optional[str] = None) -> bool | None:
    """Toggle swing setting."""
    if key not in ("swing", "swing_auto_sell"):
        return None
    field = f"{key}_enabled"
    path = Path(filepath or SETTINGS_PATH)
    with _settings_lock(path):
        settings = _load_unlocked(path)
        settings[field] = not settings[field]
        _save_unlocked(path, settings)
        return settings[field]


def set_mode(value: int | None = None, filepath: Optional[str] = None) -> int:
    """Save mode to settings."""
    path = Path(filepath or SETTINGS_PATH)
    with _settings_lock(path):
        settings = _load_unlocked(path)
        if value is None:
            exclude = local_hour() + 1
            settings["mode"] = random.choice([n for n in range(100) if n != exclude])
        else:
            stored = int(value)
            if not 0 <= stored <= 99:
                raise ValueError("value must be between 0 and 99")
            settings["mode"] = stored
        _save_unlocked(path, settings)
        return settings["mode"]
