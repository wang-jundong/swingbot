import html
import logging
from logging.handlers import RotatingFileHandler

from src.config.bindings.paths import DEX_LOG_PATH, TELEGRAM_LOG_PATH
from src.config.telegram import TELEGRAM_ERROR_MSG_MAX_LEN
from src.telegram.messages import send_error


class TelegramErrorHandler(logging.Handler):
    """Sends ERROR-level log records to Telegram via send_message."""

    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno < logging.ERROR:
            return
        try:
            msg = html.escape(self.format(record))
            if len(msg) > TELEGRAM_ERROR_MSG_MAX_LEN:
                msg = msg[: TELEGRAM_ERROR_MSG_MAX_LEN - 3] + "..."
            send_error(f"⚠️ <b>Error</b>\n {msg}")
        except Exception:
            pass  # Avoid feedback loop if send_message fails


def _make_file_logger(name: str, path: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if logger.handlers:  # Already configured
        return logger

    # File handler
    file_handler = RotatingFileHandler(path, maxBytes=5 * 1024 * 1024, backupCount=3)
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

    # Add both handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def get_telegram_logger() -> logging.Logger:
    """Logger for Telegram bot and notifications. Writes to telegram.log."""
    return _make_file_logger("cryptotrading.telegram", TELEGRAM_LOG_PATH)


def get_dex_logger() -> logging.Logger:
    """Logger for DEX-related operations. Writes to dex.log. Errors are also sent to Telegram."""
    logger = _make_file_logger("cryptotrading.dex", DEX_LOG_PATH)
    if not any(isinstance(h, TelegramErrorHandler) for h in logger.handlers):
        tg_handler = TelegramErrorHandler()
        tg_handler.setLevel(logging.ERROR)
        tg_handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
        logger.addHandler(tg_handler)
    return logger