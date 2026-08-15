"""Run the Telegram bot and swing scanner."""

import threading

from src.service.swing_service import run_swing_service
from src.telegram.bot import run_bot


def run_all_services() -> None:
    threading.Thread(target=run_swing_service, name="swing", daemon=True).start()
    run_bot()


if __name__ == "__main__":
    run_all_services()
