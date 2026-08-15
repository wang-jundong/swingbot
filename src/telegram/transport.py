"""Low-level Telegram message delivery via Bot API."""

import requests

from src.config.bindings.binding import BINDINGS

TELEGRAM_API = "https://api.telegram.org/bot"


def send_message(text: str, parse_mode: str | None = None) -> bool:
    TELEGRAM_TOKEN = BINDINGS["TELEGRAM_TOKEN"]
    TELEGRAM_CHAT_ID = BINDINGS["TELEGRAM_CHAT_ID"]
    url = f"{TELEGRAM_API}{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode  # HTML or Markdown
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code == 200
    except Exception:
        return False
