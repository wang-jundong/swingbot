"""Scan, save, buy, and auto-sell tokens on a fixed interval."""

import time

from src.config.solana import SOL_ADDRESS
from src.config.trading import (
    HOLD_DAYS,
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
from src.storage.coins import append_buy_metrics, upsert_scanned_tokens
from src.storage.settings import is_swing_auto_sell_enabled, is_swing_enabled
from src.telegram.messages import send_buy, send_sell, send_sell_alert
from src.utils.log_util import get_dex_logger
from src.utils.number_util import format_decimal, to_float
from src.utils.time_util import str_to_unix, unix_now, unix_to_str

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
                logger.info("stopped")
        except Exception:
            logger.exception("cycle failed")
            client = None
        time.sleep(SWING_INTERVAL_SEC)


def run_cycle(client: DexClient) -> None:
    run_auto_sell(client)

    tokens = scan_tokens()
    logger.info("scan %d", len(tokens))
    if not tokens:
        return

    coins, added = upsert_scanned_tokens(tokens)
    logger.info("saved %d new, %d existing", added, len(coins) - added)

    for coin in coins:
        maybe_buy(client, coin)


def run_auto_sell(client: DexClient) -> None:
    pending = get_pending_transactions()
    logger.info("sell check %d", len(pending))
    for symbol, info in pending.items():
        maybe_sell(client, symbol, info.get("net_cost") or 0.0)


def maybe_buy(client: DexClient, coin: dict) -> None:
    symbol = coin.get("symbol")
    address = coin.get("address")
    if not symbol or not address or address == SOL_ADDRESS:
        return

    buys = get_pending_buy_transactions_by_symbol(symbol)
    if len(buys) >= MAX_BUYS_PER_TOKEN:
        logger.info("skip %s: max buys", symbol)
        return

    if len(buys) == 1:
        first_price = _first_buy_price(buys)
        if first_price is None or first_price <= 0:
            logger.info("skip %s: no first price", symbol)
            return
        current = client.get_price_native(symbol)
        if current is None:
            logger.info("skip %s: no price", symbol)
            return
        threshold = first_price * SECOND_BUY_PRICE_RATIO
        if current > threshold:
            logger.info("skip %s: price above add", symbol)
            return

    balance = client.get_native_balance()
    if balance is None or balance < SWING_BUY_AMOUNT:
        logger.warning("skip %s: low SOL", symbol)
        return

    tx_hash, success, balance_before, balance_after = client.buy(symbol, SWING_BUY_AMOUNT)
    if success and tx_hash:
        logger.info("buy %s %s %s", symbol, SWING_BUY_AMOUNT, tx_hash)
        send_buy(symbol, SWING_BUY_AMOUNT, tx_hash, success, balance_before, balance_after)
        try:
            append_buy_metrics(
                address,
                coin.get("liquidity_usd"),
                coin.get("pair_age_days"),
                coin.get("filter_reason"),
                unix_to_str(unix_now()),
            )
        except Exception:
            logger.exception("failed to save buy metrics %s", symbol)
        return

    logger.warning("buy failed %s", symbol)


def maybe_sell(client: DexClient, symbol: str, net_cost: float = 0.0) -> None:
    if not symbol or symbol == SOL_ADDRESS:
        return

    buys = get_pending_buy_transactions_by_symbol(symbol)
    if not buys:
        return

    current = client.get_price_native(symbol)
    if current is None:
        logger.info("skip sell %s: no price", symbol)
        return

    balance = client.get_balance(symbol)
    if balance is None or balance <= 0:
        logger.info("skip sell %s: no balance", symbol)
        return

    if net_cost <= 0:
        logger.info("skip sell %s: no cost", symbol)
        return

    value = current * balance
    pnl = value - net_cost
    threshold = SWING_BUY_AMOUNT * SELL_PNL_RATIO
    hold_expired = _hold_expired(buys)
    if not hold_expired and pnl < threshold:
        logger.info("skip sell %s: pnl %s", symbol, format_decimal(pnl))
        return

    reason = "hold" if hold_expired else "target"
    if is_swing_auto_sell_enabled():
        tx_hash, success, pnl, balance_before, balance_after = client.sell(
            symbol, SWING_SELL_AMOUNT, reason=reason,
        )
        if success and tx_hash:
            logger.info("sell %s %s pnl=%s %s", symbol, reason, format_decimal(pnl), tx_hash)
            send_sell(
                symbol, SWING_SELL_AMOUNT, tx_hash, success, pnl,
                balance_before, balance_after, reason,
            )
            return
        logger.warning("sell failed %s", symbol)
        return

    logger.info("alert sell %s %s", symbol, reason)
    send_sell_alert(symbol, balance, pnl, reason)


def _first_buy_price(buys: list[dict]) -> float | None:
    first = min(buys, key=lambda row: str(row.get("timestamp") or ""))
    return to_float(first.get("price"))


def _hold_expired(buys: list[dict]) -> bool:
    first = min(buys, key=lambda row: str(row.get("timestamp") or ""))
    started = str_to_unix(first.get("timestamp"))
    if started is None:
        return False
    return unix_now() - started >= HOLD_DAYS * 86400
