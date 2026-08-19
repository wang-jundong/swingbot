"""Run the Telegram bot, swing scanner, and token dashboard."""

import threading

from src.service.swing_service import run_swing_service
from src.telegram.bot import run_bot
from src.web.server import run_web_server


def run_all_services() -> None:
    threading.Thread(target=run_swing_service, name="swing", daemon=True).start()
    threading.Thread(target=run_web_server, name="web", daemon=True).start()
    run_bot()


if __name__ == "__main__":
    run_all_services()
