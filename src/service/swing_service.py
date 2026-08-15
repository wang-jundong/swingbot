"""Scan, save, buy, and auto-sell tokens on a fixed interval."""

import time

from src.config.solana import SOL_ADDRESS
from src.config.trading import (
    MAX_BUYS_PER_TOKEN,
    SECOND_BUY_PRICE_RATIO,
    SELL_PNL_RATIO,
    SWING_BUY_AMOUNT,
    SWING_INTERVAL_SEC,
    SWING_SELL_AMOUNT,
)
from src.dex.history.transaction import (
    get_pending_buy_transactions_by_symbol,
    get_pending_transactions,
)
from src.dex.solana.client import DexClient
from src.integrations.birdeye import scan_tokens
from src.storage.coins import upsert_scanned_tokens
from src.storage.settings import is_swing_auto_sell_enabled, is_swing_enabled
from src.telegram.messages import send_buy, send_sell, send_sell_alert
from src.utils.log_util import get_dex_logger
from src.utils.number_util import format_decimal, to_float

logger = get_dex_logger()


def run_swing_service() -> None:
    client: DexClient | None = None
    while True:
        try:
            if is_swing_enabled():
                if client is None:
                    client = DexClient()
                run_cycle(client)
            else:
                logger.info("Swing bot stopped; skip cycle")
        except Exception:
            logger.exception("Swing cycle failed")
            client = None
        time.sleep(SWING_INTERVAL_SEC)


def run_cycle(client: DexClient) -> None:
    run_auto_sell(client)

    tokens = scan_tokens()
    logger.info("Swing scan matched %d token(s)", len(tokens))
    if not tokens:
        return

    coins, added = upsert_scanned_tokens(tokens)
    logger.info("Swing saved %d new token(s), %d already stored", added, len(coins) - added)

    for coin in coins:
        maybe_buy(client, coin)


def run_auto_sell(client: DexClient) -> None:
    pending = get_pending_transactions()
    logger.info("Swing sell check %d position(s)", len(pending))
    for symbol, info in pending.items():
        maybe_sell(client, symbol, info.get("net_cost") or 0.0)


def maybe_buy(client: DexClient, coin: dict) -> None:
    symbol = coin.get("symbol")
    address = coin.get("address")
    if not symbol or not address or address == SOL_ADDRESS:
        return

    buys = get_pending_buy_transactions_by_symbol(symbol)
    if len(buys) >= MAX_BUYS_PER_TOKEN:
        logger.info("Skip %s: already %d buy(s)", symbol, len(buys))
        return

    if len(buys) == 1:
        first_price = _first_buy_price(buys)
        if first_price is None or first_price <= 0:
            logger.info("Skip %s: missing first buy price", symbol)
            return
        current = client.get_price_native(symbol)
        if current is None:
            logger.info("Skip %s: no current price", symbol)
            return
        threshold = first_price * SECOND_BUY_PRICE_RATIO
        if current > threshold:
            logger.info(
                "Skip %s: price %s > %.0f%% of first buy %s",
                symbol,
                format_decimal(current),
                SECOND_BUY_PRICE_RATIO * 100,
                format_decimal(first_price),
            )
            return

    balance = client.get_native_balance()
    if balance is None or balance < SWING_BUY_AMOUNT:
        logger.warning("Skip %s: insufficient SOL (%s)", symbol, balance)
        return

    tx_hash, success, balance_before, balance_after = client.buy(symbol, SWING_BUY_AMOUNT)
    if success and tx_hash:
        logger.info("Bought %s amount=%s tx=%s", symbol, SWING_BUY_AMOUNT, tx_hash)
        send_buy(symbol, SWING_BUY_AMOUNT, tx_hash, success, balance_before, balance_after)
        return

    logger.warning("Buy failed for %s", symbol)


def maybe_sell(client: DexClient, symbol: str, net_cost: float = 0.0) -> None:
    if not symbol or symbol == SOL_ADDRESS:
        return

    buys = get_pending_buy_transactions_by_symbol(symbol)
    if not buys:
        return

    current = client.get_price_native(symbol)
    if current is None:
        logger.info("Skip sell %s: no current price", symbol)
        return

    balance = client.get_balance(symbol)
    if balance is None or balance <= 0:
        logger.info("Skip sell %s: no token balance", symbol)
        return

    if net_cost <= 0:
        logger.info("Skip sell %s: missing net cost", symbol)
        return

    value = current * balance
    pnl = value - net_cost
    threshold = SWING_BUY_AMOUNT * SELL_PNL_RATIO
    if pnl < threshold:
        logger.info(
            "Skip sell %s: pnl %s < %.0f%% of buy amount %s",
            symbol,
            format_decimal(pnl),
            SELL_PNL_RATIO * 100,
            format_decimal(SWING_BUY_AMOUNT),
        )
        return

    if is_swing_auto_sell_enabled():
        tx_hash, success, pnl, balance_before, balance_after = client.sell(symbol, SWING_SELL_AMOUNT)
        if success and tx_hash:
            logger.info("Sold %s amount=%s tx=%s pnl=%s", symbol, SWING_SELL_AMOUNT, tx_hash, format_decimal(pnl))
            send_sell(symbol, SWING_SELL_AMOUNT, tx_hash, success, pnl, balance_before, balance_after)
            return
        logger.warning("Sell failed for %s", symbol)
        return

    logger.info("Sell target hit for %s; auto-sell off, alerting", symbol)
    send_sell_alert(symbol, balance, pnl)


def _first_buy_price(buys: list[dict]) -> float | None:
    first = min(buys, key=lambda row: str(row.get("timestamp") or ""))
    return to_float(first.get("price"))
