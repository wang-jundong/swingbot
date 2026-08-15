"""Custom Telegram bot filters."""

from telegram.ext import filters

from src.config.bindings.binding import BINDINGS


def _get_allowed_ids() -> list[int]:
    raw = BINDINGS.get("TELEGRAM_ALLOWED_USERS", "").strip()
    if not raw:
        return []
    ids: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if part and part.isdigit():
            ids.append(int(part))
    return ids


class _AllowedUsersFilter(filters.UpdateFilter):
    """Pass only when user is in TELEGRAM_ALLOWED_USERS; if unset, deny all."""

    def filter(self, update) -> bool:  # type: ignore[override]
        if update is None:
            return False

        user = getattr(update, "effective_user", None)
        if user is None:
            return False

        allowed = _get_allowed_ids()
        if not allowed:
            return False

        return user.id in allowed


allowed_users = _AllowedUsersFilter()
