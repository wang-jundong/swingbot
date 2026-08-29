"""JSON payloads for the token dashboard."""

import threading

from src.dex.history.daily_pnl import date_key, load_daily_pnl
from src.dex.history.trade_stats import get_trade_stats
from src.dex.history.transaction import get_pending_transactions, pnl_native
from src.dex.solana.client import DexClient
from src.dex.solana.common.spl import get_owner_token_balances
from src.dex.solana.jupiter.markets import fetch_token_markets
from src.backtest.data import (
    fetch_all,
    fetch_mint,
    load_cached_ohlcv,
    load_universe,
    load_wallet_fills,
)
from src.config.backtest import CANDLE_INTERVAL_SEC
from src.storage.coins import get_all_tokens
from src.utils.number_util import to_float
from src.utils.time_util import unix_now
from src.web.chart_spec import listing_unix, prepare_candles

_dex_client: DexClient | None | bool = None


def _as_list(value) -> list:
    if isinstance(value, list):
        return list(value)
    if value is None:
        return []
    return [value]


def _last(values: list):
    return values[-1] if values else None


def _sum(values: list) -> float:
    total = 0.0
    for value in values:
        number = to_float(value)
        if number is not None:
            total += number
    return total


def _status(symbol: str, buy_count: int, sell_count: int, pending_symbols: set[str]) -> str | None:
    if symbol.strip() in pending_symbols:
        return "open"
    if sell_count > 0 or buy_count > 0:
        return "sold"
    return None


def serialize_token(coin: dict, pending_symbols: set[str]) -> dict | None:
    liquidity = _as_list(coin.get("liquidity"))
    volume_24h_usd = _as_list(coin.get("volume_24h_usd"))
    pair_age = _as_list(coin.get("pair_age"))
    filter_reason = _as_list(coin.get("filter_reason"))
    buy_time = _as_list(coin.get("buy_time"))
    pnl = _as_list(coin.get("pnl"))
    sell_reason = _as_list(coin.get("sell_reason"))
    sell_time = _as_list(coin.get("sell_time"))
    scan_count = _as_list(coin.get("scan_count"))
    sell_count = max(len(pnl), len(sell_reason), len(sell_time))
    buy_count = len(buy_time)
    symbol = coin.get("symbol") or ""
    status = _status(symbol, buy_count, sell_count, pending_symbols)
    if status is None:
        return None
    n_buys = max(
        len(liquidity),
        len(volume_24h_usd),
        len(pair_age),
        len(filter_reason),
        len(buy_time),
    )

    buys = []
    for i in range(n_buys):
        buys.append({
            "time": buy_time[i] if i < len(buy_time) else None,
            "liquidity": liquidity[i] if i < len(liquidity) else None,
            "volume_24h_usd": volume_24h_usd[i] if i < len(volume_24h_usd) else None,
            "pair_age": pair_age[i] if i < len(pair_age) else None,
            "filter_reason": filter_reason[i] if i < len(filter_reason) else None,
        })

    sells = []
    for i in range(sell_count):
        sells.append({
            "time": sell_time[i] if i < len(sell_time) else None,
            "pnl": pnl[i] if i < len(pnl) else None,
            "reason": sell_reason[i] if i < len(sell_reason) else None,
        })

    scans = _serialize_scans(coin.get("scans"))
    scan_total = sum(len(group) for group in scans)
    if not scan_total:
        scan_total = int(_sum(scan_count)) if scan_count else 0

    return {
        "name": coin.get("name") or "",
        "symbol": symbol,
        "address": coin.get("address") or "",
        "status": status,
        "buy_count": buy_count,
        "sell_count": sell_count,
        "scan_total": scan_total,
        "scan_count": [int(v or 0) for v in scan_count],
        "total_pnl": round(_sum(pnl), 6) if pnl else None,
        "net_pnl": None,
        "liquidity": None,
        "liquidity_usd": None,
        "pair_age": None,
        "volume_24h": None,
        "txns_24h": None,
        "last_buy_time": _last(buy_time),
        "last_pair_age": _last(pair_age),
        "buys": buys,
        "sells": sells,
        "scans": scans,
    }


def _serialize_scans(value) -> list[list[dict]]:
    if not isinstance(value, list) or not value:
        return []
    groups = [value] if isinstance(value[0], dict) else value
    rounds = []
    for group in groups:
        if not isinstance(group, list):
            continue
        rows = []
        for item in group:
            if not isinstance(item, dict):
                continue
            rows.append({
                "scan_time": item.get("scan_time"),
                "liquidity_usd": item.get("liquidity_usd"),
                "volume_24h_usd": item.get("volume_24h_usd"),
                "price": item.get("price"),
                "filter_reason": item.get("filter_reason"),
            })
        if rows:
            rounds.append(rows)
    return rounds


def backtest_ohlcv_payload(address: str) -> dict | None:
    """Full 5m candles and wallet fills for one mint."""
    mint = (address or "").strip()
    if not mint or len(mint) > 64 or not mint.isalnum():
        return None
    cached = load_cached_ohlcv(mint)
    if not cached:
        return None
    universe = {
        coin.get("address"): coin
        for coin in load_universe()
        if coin.get("address")
    }
    coin = universe.get(mint) or {}
    fills = [
        fill for fill in load_wallet_fills()
        if fill.get("address") == mint
    ]
    candles = prepare_candles(cached.get("candles") or [], now=unix_now())
    return {
        "name": coin.get("name") or "",
        "symbol": coin.get("symbol") or "",
        "address": mint,
        "buy_time": _as_list(coin.get("buy_time")),
        "market": cached.get("market") or coin.get("market"),
        "interval_sec": cached.get("interval_sec") or CANDLE_INTERVAL_SEC,
        "t": candles["t"],
        "o": candles["o"],
        "h": candles["h"],
        "l": candles["l"],
        "c": candles["c"],
        "v": candles["v"],
        "fills": fills,
        "registered_at": listing_unix(coin),
    }


def refresh_mint_ohlcv(address: str) -> dict | None:
    """Fetch latest 5m candles for one mint, then return the chart payload."""
    mint = (address or "").strip()
    if not mint or len(mint) > 64 or not mint.isalnum():
        return None
    fetch_mint(mint)
    return backtest_ohlcv_payload(mint)


def tokens_payload(*, live: bool = False) -> dict:
    pending = get_pending_transactions()
    pending_symbols = {str(symbol).strip() for symbol in pending}
    tokens = [
        token
        for token in (
            serialize_token(coin, pending_symbols) for coin in get_all_tokens()
        )
        if token is not None
    ]
    tokens.sort(key=lambda token: token.get("last_buy_time") or "", reverse=True)
    if live:
        _attach_market_stats(tokens)
        _attach_net_pnls(tokens, pending)
    open_count = sum(1 for token in tokens if token["status"] == "open")
    sold_count = sum(
        1
        for token in tokens
        if token["status"] == "sold" or token["sell_count"] > 0
    )
    stats = get_trade_stats()
    return {
        "tokens": tokens,
        "summary": {
            "token_count": len(tokens),
            "open_count": open_count,
            "sold_count": sold_count,
            "realized_pnl": float(stats.get("pnl") or 0),
            "daily_pnl": load_daily_pnl(),
            "today": date_key(),
        },
    }


def _client() -> DexClient | None:
    global _dex_client
    if _dex_client is False:
        return None
    if _dex_client is None:
        try:
            _dex_client = DexClient()
        except Exception:
            _dex_client = False
            return None
    return _dex_client


def _attach_market_stats(tokens: list[dict]) -> None:
    addresses = [token["address"] for token in tokens if token.get("address")]
    if not addresses:
        return
    markets = fetch_token_markets(addresses)
    for token in tokens:
        stats = markets.get(token.get("address") or "")
        if not stats:
            continue
        token["liquidity"] = stats.get("liquidity")
        token["liquidity_usd"] = stats.get("liquidity_usd")
        token["pair_age"] = stats.get("pair_age")
        token["volume_24h"] = stats.get("volume_24h")
        token["txns_24h"] = stats.get("txns_24h")
        token["price"] = stats.get("price")


def _attach_net_pnls(tokens: list[dict], pending: dict) -> None:
    if not pending:
        return
    client = _client()
    balances: dict[str, float] | None = None
    if client is not None:
        try:
            balances = get_owner_token_balances(client.rpc_url, str(client.keypair.pubkey()))
        except Exception:
            balances = None
    by_symbol = {str(token["symbol"]).strip(): token for token in tokens}
    for symbol, row in pending.items():
        token = by_symbol.get(str(symbol).strip())
        if token is None:
            continue
        mint = token.get("address") or ""
        price = token.get("price")
        balance = None if balances is None or not mint else balances.get(mint, 0.0)
        value = pnl_native(price, balance, row["net_cost"])
        token["net_pnl"] = None if value is None else round(value, 6)


_refresh_lock = threading.Lock()
_refresh = {
    "running": False,
    "done": 0,
    "total": 0,
    "symbol": "",
    "address": "",
    "message": "",
    "error": None,
    "summary": None,
}


def candle_refresh_status() -> dict:
    with _refresh_lock:
        return dict(_refresh)


def start_candle_refresh() -> dict:
    with _refresh_lock:
        if _refresh["running"]:
            return {"started": False, **dict(_refresh)}
        _refresh.update({
            "running": True,
            "done": 0,
            "total": 0,
            "symbol": "",
            "address": "",
            "message": "Updating wallet fills…",
            "error": None,
            "summary": None,
        })
    threading.Thread(target=_run_candle_refresh, daemon=True).start()
    return {"started": True, **candle_refresh_status()}


def _run_candle_refresh() -> None:
    def on_progress(done: int, total: int, row: dict) -> None:
        with _refresh_lock:
            _refresh["done"] = done
            _refresh["total"] = total
            _refresh["symbol"] = str(row.get("symbol") or "")
            _refresh["address"] = str(row.get("address") or "")
            _refresh["message"] = str(row.get("error") or "ok")

    try:
        summary = fetch_all(on_progress=on_progress, refresh_fills=True)
        with _refresh_lock:
            _refresh["summary"] = summary
            _refresh["message"] = "done"
            _refresh["done"] = int(summary.get("tokens") or _refresh["done"])
            _refresh["total"] = int(summary.get("tokens") or _refresh["total"])
    except Exception as exc:
        with _refresh_lock:
            _refresh["error"] = str(exc)
            _refresh["message"] = "failed"
    finally:
        with _refresh_lock:
            _refresh["running"] = False

