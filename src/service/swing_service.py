"""Scan, save, buy, and auto-sell tokens on a fixed interval."""

from concurrent.futures import ThreadPoolExecutor
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
from src.dex.dual_mode import execute_dual_mode_trade
from src.dex.history.transaction import (
    get_pending_buy_transactions_by_symbol,
    get_pending_transactions,
    is_hold_expired,
)
from src.dex.solana.client import DexClient
from src.dex.solana.common.spl import get_owner_token_balances
from src.dex.solana.jupiter.markets import fetch_token_markets
from src.integrations.birdeye import scan_tokens
from src.storage.coins import append_buy_metrics, get_all_tokens, upsert_scanned_tokens
from src.storage.settings import is_swing_auto_sell_enabled, is_swing_enabled
from src.telegram.messages import send_buy, send_sell, send_sell_alert
from src.utils.log_util import get_dex_logger
from src.utils.number_util import format_decimal, to_float
from src.utils.time_util import unix_now, unix_to_str

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
    if not pending:
        return

    coins_by_symbol = {
        str(coin.get("symbol") or "").strip(): coin
        for coin in get_all_tokens()
    }
    addresses = []
    for symbol in pending:
        coin = coins_by_symbol.get(str(symbol).strip())
        address = (coin or {}).get("address")
        if address:
            addresses.append(address)

    markets, balances = _load_sell_quotes(client, addresses)
    if balances is None:
        return

    for symbol, info in pending.items():
        coin = coins_by_symbol.get(str(symbol).strip()) or {}
        mint = coin.get("address") or ""
        stats = markets.get(mint) or {}
        maybe_sell(
            client,
            symbol,
            info.get("net_cost") or 0.0,
            _pending_buys(info),
            stats.get("price"),
            None if not mint else balances.get(mint, 0.0),
        )


def _load_sell_quotes(
    client: DexClient,
    addresses: list[str],
) -> tuple[dict[str, dict], dict[str, float] | None]:
    """Batch Jupiter prices and wallet balances for open positions."""
    markets: dict[str, dict] = {}
    balances: dict[str, float] | None = None
    with ThreadPoolExecutor(max_workers=2) as pool:
        market_future = pool.submit(fetch_token_markets, addresses) if addresses else None
        balance_future = pool.submit(
            get_owner_token_balances,
            client.rpc_url,
            str(client.keypair.pubkey()),
        )
        if market_future is not None:
            try:
                markets = market_future.result()
            except Exception:
                logger.exception("failed to load market prices")
        try:
            balances = balance_future.result()
        except Exception:
            logger.exception("failed to load wallet balances")
    return markets, balances


def _pending_buys(info: dict) -> list[dict]:
    return [
        row
        for row in info.get("rows") or []
        if str(row.get("action") or "").lower() == "buy"
    ]


def maybe_buy(client: DexClient, coin: dict) -> None:
    symbol = coin.get("symbol")
    address = coin.get("address")
    if not symbol or not address or address == SOL_ADDRESS:
        return

    if _already_sold(coin):
        logger.info("skip %s: already sold", symbol)
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

    tx_hash, success, balance_before, balance_after = execute_dual_mode_trade(
        "buy", client.buy, symbol, SWING_BUY_AMOUNT
    )
    if success and tx_hash:
        logger.info("buy %s %s %s", symbol, SWING_BUY_AMOUNT, tx_hash)
        send_buy(symbol, SWING_BUY_AMOUNT, tx_hash, success, balance_before, balance_after)
        try:
            scan = _last_scan(coin)
            append_buy_metrics(
                address,
                scan.get("liquidity_usd", coin.get("liquidity_usd")),
                coin.get("pair_age_days"),
                scan.get("filter_reason") or coin.get("filter_reason"),
                scan.get("scan_time") or unix_to_str(unix_now()),
                scan.get("volume_24h_usd", coin.get("volume_24h_usd")),
            )
        except Exception:
            logger.exception("failed to save buy metrics %s", symbol)
        return

    logger.warning("buy failed %s", symbol)


def maybe_sell(
    client: DexClient,
    symbol: str,
    net_cost: float,
    buys: list[dict],
    current: float | None,
    balance: float | None,
) -> None:
    if not symbol or symbol == SOL_ADDRESS:
        return

    if not buys:
        return

    if current is None:
        logger.info("skip sell %s: no price", symbol)
        return

    if balance is None or balance <= 0:
        logger.info("skip sell %s: no balance", symbol)
        return

    if net_cost <= 0:
        logger.info("skip sell %s: no cost", symbol)
        return

    value = current * balance
    pnl = value - net_cost
    threshold = SWING_BUY_AMOUNT * SELL_PNL_RATIO
    hold_expired = is_hold_expired(buys)
    if not hold_expired and pnl < threshold:
        logger.info("skip sell %s: pnl %s", symbol, format_decimal(pnl))
        return

    reason = "hold" if hold_expired else "target"
    if is_swing_auto_sell_enabled():
        tx_hash, success, pnl, balance_before, balance_after = execute_dual_mode_trade(
            "sell", client.sell, symbol, SWING_SELL_AMOUNT, reason=reason,
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


def _already_sold(coin: dict) -> bool:
    sell_time = coin.get("sell_time")
    if isinstance(sell_time, list):
        return any(sell_time)
    return bool(sell_time)


def _last_scan(coin: dict) -> dict:
    rounds = coin.get("scans") or []
    if not rounds:
        return {}
    last_round = rounds[-1]
    if isinstance(last_round, dict):
        return last_round
    if isinstance(last_round, list) and last_round:
        last = last_round[-1]
        return last if isinstance(last, dict) else {}
    return {}


def _first_buy_price(buys: list[dict]) -> float | None:
    first = min(buys, key=lambda row: str(row.get("timestamp") or ""))
    return to_float(first.get("price"))
