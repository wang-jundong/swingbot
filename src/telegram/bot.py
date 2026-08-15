"""Bot entry point."""

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from src.config.bindings.binding import BINDINGS
from src.dex.solana.client import DexClient as SolanaDexClient
from src.telegram.commands.main import on_main_keyboard, start
from src.telegram.filters import allowed_users
from src.telegram.handlers.trade import (
    on_buy_amount,
    on_buy_token,
    on_sell_amount,
    on_sell_token,
)
from src.telegram.handlers.settings import (
    on_settings_swing_auto_sell,
    on_settings_swing_toggle,
)
from src.utils.log_util import get_telegram_logger

logger = get_telegram_logger()

try:
    solana_dex_client = SolanaDexClient()
except Exception as e:
    logger.error("Failed to initialize Solana DexClient: %s", e)
    solana_dex_client = None


def run_bot() -> None:
    token = BINDINGS["TELEGRAM_TOKEN"]
    app = Application.builder().token(token).build()
    app.bot_data["dex_client"] = solana_dex_client

    app.add_handler(CommandHandler("start", start, filters=allowed_users))
    app.add_handler(MessageHandler(allowed_users & filters.Regex("^(Buy|Sell|History|Settings)$"), on_main_keyboard))
    app.add_handler(CallbackQueryHandler(on_buy_token, pattern=r"^buy:[^:]+$"))
    app.add_handler(CallbackQueryHandler(on_buy_amount, pattern=r"^buy_amount:"))
    app.add_handler(CallbackQueryHandler(on_sell_token, pattern=r"^sell:[^:]+$"))
    app.add_handler(CallbackQueryHandler(on_sell_amount, pattern=r"^sell_amount:"))
    app.add_handler(CallbackQueryHandler(on_settings_swing_toggle, pattern=r"^settings_swing_toggle$"))
    app.add_handler(CallbackQueryHandler(on_settings_swing_auto_sell, pattern=r"^settings_swing_auto_sell$"))

    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    run_bot()
