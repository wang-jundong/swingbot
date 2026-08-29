"""Load bought mints and fetch wallet fills plus GeckoTerminal 5m candles."""

from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from src.config.backtest import (
    CANDLE_INTERVAL_SEC,
    GECKO_MAX_OHLCV_PAGES,
    HOLD_WINDOW_SEC,
    LOOKBACK_SEC,
    MAX_PAGES_PER_MARKET,
    OHLCV_DIR,
    REQUEST_PAUSE_SEC,
    UNIVERSE_PATH,
    WALLET_FILLS_PATH,
)
from src.config.bindings.binding import BINDINGS
from src.config.bindings.paths import COINS_PATH
from src.config.solana import LAMPORTS_PER_SOL, SOL_ADDRESS
from src.integrations.geckoterminal import (
    filter_window,
    get_pool_ohlcv,
    get_token_pools,
    parse_ohlcv_list,
    pool_meta,
    select_pool,
)
from src.integrations.helius import get_transactions_page
from src.storage.coins import load_coins
from src.utils.number_util import to_float
from src.utils.time_util import str_to_unix, unix_now, unix_to_str

_UNIVERSE_LOCK = threading.Lock()


def load_bought_coins(filepath: str | None = None) -> list[dict]:
    """Coins from coins_solana.json that have at least one buy_time."""
    coins = []
    for coin in load_coins(filepath or COINS_PATH):
        buys = _as_list(coin.get("buy_time"))
        address = coin.get("address")
        if not address or not buys:
            continue
        buy_unix = [ts for ts in (str_to_unix(value) for value in buys) if ts]
        coins.append({
            "name": coin.get("name"),
            "symbol": coin.get("symbol"),
            "address": address,
            "buy_time": buys,
            "buy_unix": buy_unix,
            "pair_age": _first(coin.get("pair_age")),
            "liquidity": _first(coin.get("liquidity")),
            "volume_24h_usd": _first(coin.get("volume_24h_usd")),
        })
    return coins


def discover_geckoterminal_pool(mint: str) -> dict:
    """Highest-liquidity GeckoTerminal SOL pool for the mint."""
    pools = get_token_pools(mint)
    chosen = select_pool(pools, mint)
    if not chosen:
        return {"pool": None, "market": None, "token_side": "base", "error": "no geckoterminal pool"}
    return pool_meta(chosen, mint)


def fetch_wallet_fills(
    coins: list[dict],
    *,
    force: bool = False,
) -> list[dict]:
    mints = {coin["address"] for coin in coins}
    cached = {} if force else _read_json(WALLET_FILLS_PATH, {})
    if isinstance(cached, dict) and cached.get("mints") == sorted(mints):
        return cached.get("fills") or []

    wallet = BINDINGS["SOLANA_PUBLIC_ADDRESS"].strip()
    symbols = {coin["address"]: coin.get("symbol") for coin in coins}
    time_from, time_to = _wallet_window(coins)
    fills: list[dict] = []
    pagination = None
    pages = 0
    while pages < MAX_PAGES_PER_MARKET:
        rows, pagination = get_transactions_page(
            wallet,
            time_from=time_from,
            time_to=time_to,
            details="full",
            pagination_token=pagination,
            extra_filters={"tokenAccounts": "balanceChanged"},
        )
        pages += 1
        if not rows:
            break
        for tx in rows:
            fills.extend(_fills_from_tx(tx, wallet, mints, symbols))
        if not pagination:
            break
        time.sleep(REQUEST_PAUSE_SEC)

    fills.sort(key=lambda row: (row.get("block_time") or 0, row.get("address") or ""))
    _write_json(WALLET_FILLS_PATH, {"mints": sorted(mints), "fills": fills})
    return fills


def fetch_ohlcv(
    mint: str,
    market: str,
    time_from: int,
    time_to: int,
    *,
    force: bool = False,
    token: str | None = None,
) -> list[dict]:
    path = _ohlcv_path(mint)
    cached = {} if force else (_read_json(path, {}) or {})
    existing = [] if force else list(cached.get("candles") or [])
    fetch_from = int(time_from)
    if existing:
        last = max(int(row.get("unix_time") or 0) for row in existing)
        if last >= int(time_to):
            return existing
        fetch_from = max(fetch_from, last - CANDLE_INTERVAL_SEC)

    collected: list = []
    pages = 0
    before = int(time_to) + CANDLE_INTERVAL_SEC
    while pages < GECKO_MAX_OHLCV_PAGES:
        rows = get_pool_ohlcv(
            market,
            timeframe="minute",
            aggregate=CANDLE_INTERVAL_SEC // 60,
            before_timestamp=before,
            token=token or "base",
        )
        pages += 1
        if not rows:
            break
        collected.extend(rows)
        stamps = [
            int(row[0])
            for row in rows
            if isinstance(row, (list, tuple)) and row
        ]
        if not stamps:
            break
        oldest = min(stamps)
        if oldest <= fetch_from:
            break
        if oldest >= before:
            break
        before = oldest

    incoming = filter_window(parse_ohlcv_list(collected), fetch_from, time_to)
    candles = _merge_candles(existing, incoming)
    candles = filter_window(candles, time_from, time_to)
    OHLCV_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(path, {
        "address": mint,
        "source": "geckoterminal",
        "market": market,
        "interval_sec": CANDLE_INTERVAL_SEC,
        "time_from": time_from,
        "time_to": time_to,
        "pages": pages,
        "candles": candles,
    })
    return candles


def mint_window(coin: dict, now: int | None = None) -> tuple[int, int]:
    now = now or unix_now()
    buys = coin.get("buy_unix") or []
    start = min(buys) - LOOKBACK_SEC if buys else now - LOOKBACK_SEC
    end = (max(buys) + HOLD_WINDOW_SEC) if buys else now
    return int(start), int(min(end, now))


def fetch_mint(mint: str, *, force: bool = False) -> dict:
    """Incremental 5m candles for one bought mint. Updates universe.json."""
    mint = (mint or "").strip()
    coin = next((row for row in load_bought_coins() if row.get("address") == mint), None)
    if coin is None:
        prev = next((row for row in load_universe() if row.get("address") == mint), None)
        if prev is None:
            return {"address": mint, "candles": 0, "error": "unknown mint"}
        coin = {
            "name": prev.get("name"),
            "symbol": prev.get("symbol"),
            "address": mint,
            "buy_time": prev.get("buy_time") or [],
            "buy_unix": prev.get("buy_unix") or [],
            "pair_age": prev.get("pair_age"),
            "liquidity": prev.get("liquidity"),
            "volume_24h_usd": prev.get("volume_24h_usd"),
        }
    previous = {
        row.get("address"): row
        for row in load_universe()
        if row.get("address")
    }
    fills_by_mint: dict[str, int] = {}
    for fill in load_wallet_fills():
        address = fill.get("address")
        fills_by_mint[address] = fills_by_mint.get(address, 0) + 1
    row = _fetch_coin_candles(
        coin,
        previous=previous,
        fills_by_mint=fills_by_mint,
        now=unix_now(),
        force=force,
    )
    _upsert_universe_row(row)
    return row


def _fetch_coin_candles(
    coin: dict,
    *,
    previous: dict,
    fills_by_mint: dict[str, int],
    now: int,
    force: bool,
) -> dict:
    mint = coin["address"]
    time_from, time_to = mint_window(coin, now)
    cached = None if force else load_cached_ohlcv(mint)
    prev = previous.get(mint) or {}
    market_info = _reuse_pool(cached, prev) if not force else {}
    if not (market_info.get("market") or market_info.get("pool")):
        try:
            market_info = discover_geckoterminal_pool(mint)
        except Exception as exc:
            market_info = {
                "pool": None,
                "market": None,
                "token_side": "base",
                "error": str(exc),
            }
    market = market_info.get("market") or market_info.get("pool")
    existing = list((cached or {}).get("candles") or [])
    try:
        if not market:
            candles = existing
            error = market_info.get("error") or "no geckoterminal pool"
        else:
            candles = fetch_ohlcv(
                mint,
                market,
                time_from,
                time_to,
                force=force,
                token=market_info.get("token_side") or "base",
            )
            error = None
    except Exception as exc:
        candles = existing
        error = str(exc)
    return {
        **coin,
        **market_info,
        "time_from": time_from,
        "time_to": time_to,
        "candles": len(candles),
        "fills": fills_by_mint.get(mint, 0),
        "error": error,
    }


def fetch_all(
    *,
    limit: int | None = None,
    force: bool = False,
    workers: int = 1,
    refresh_fills: bool = False,
    on_progress=None,
) -> dict:
    coins = load_bought_coins()
    if limit is not None:
        coins = coins[: max(0, limit)]
    previous = {
        row.get("address"): row
        for row in load_universe()
        if row.get("address")
    }
    print(f"universe {len(coins)} bought mints", flush=True)

    print("wallet fills...", flush=True)
    fills = fetch_wallet_fills(coins, force=force or refresh_fills)
    fills_by_mint: dict[str, int] = {}
    for fill in fills:
        address = fill.get("address")
        fills_by_mint[address] = fills_by_mint.get(address, 0) + 1
    print(f"wallet fills {len(fills)}", flush=True)

    OHLCV_DIR.mkdir(parents=True, exist_ok=True)
    now = unix_now()
    if on_progress:
        on_progress(0, len(coins), {"symbol": "", "error": "starting"})

    def _job(coin: dict) -> dict:
        return _fetch_coin_candles(
            coin,
            previous=previous,
            fills_by_mint=fills_by_mint,
            now=now,
            force=force,
        )

    universe: list[dict] = []
    done = 0
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(_job, coin): coin for coin in coins}
        for future in as_completed(futures):
            coin = futures[future]
            try:
                row = future.result()
            except Exception as exc:
                row = {**coin, "candles": 0, "fills": 0, "error": str(exc)}
            universe.append(row)
            done += 1
            _upsert_universe_row(row)
            print(
                f"[{done}/{len(coins)}] {row.get('symbol') or '?'} "
                f"candles={row.get('candles')} fills={row.get('fills')} "
                f"pool={(row.get('pool') or '')[:8]} "
                f"{row.get('error') or 'ok'}",
                flush=True,
            )
            if on_progress:
                on_progress(done, len(coins), row)

    universe.sort(key=lambda row: (row.get("buy_unix") or [0])[0])
    with _UNIVERSE_LOCK:
        _write_json(UNIVERSE_PATH, universe)
    ok = sum(1 for row in universe if (row.get("candles") or 0) > 0)
    summary = {
        "tokens": len(universe),
        "with_candles": ok,
        "wallet_fills": len(fills),
        "universe_path": str(UNIVERSE_PATH),
        "ohlcv_dir": str(OHLCV_DIR),
    }
    print(
        f"done tokens={summary['tokens']} "
        f"with_candles={summary['with_candles']} "
        f"fills={summary['wallet_fills']}",
        flush=True,
    )
    return summary


def _fills_from_tx(
    tx: dict,
    wallet: str,
    mints: set[str],
    symbols: dict[str, str | None],
) -> list[dict]:
    meta = tx.get("meta") or {}
    if meta.get("err"):
        return []
    block_time = tx.get("blockTime")
    signature = ((tx.get("transaction") or {}).get("signatures") or [None])[0]
    sol_before, sol_after = _native_sol(tx, wallet)
    sol_delta = sol_after - sol_before

    token_delta: dict[str, float] = {}
    wsol_delta = 0.0
    pre = {
        (row.get("owner"), row.get("mint")): _ui_amount(row)
        for row in meta.get("preTokenBalances") or []
    }
    post = {
        (row.get("owner"), row.get("mint")): _ui_amount(row)
        for row in meta.get("postTokenBalances") or []
    }
    for owner, token_mint in set(pre) | set(post):
        if owner != wallet or not token_mint:
            continue
        delta = post.get((owner, token_mint), 0.0) - pre.get((owner, token_mint), 0.0)
        if token_mint == SOL_ADDRESS:
            wsol_delta += delta
        elif token_mint in mints:
            token_delta[token_mint] = token_delta.get(token_mint, 0.0) + delta

    quote = wsol_delta if wsol_delta != 0 else sol_delta
    fills = []
    for mint, amount in token_delta.items():
        if amount == 0:
            continue
        price = abs(quote / amount) if amount else None
        fills.append({
            "address": mint,
            "symbol": symbols.get(mint),
            "signature": signature,
            "block_time": block_time,
            "timestamp": unix_to_str(int(block_time)) if block_time else None,
            "action": "buy" if amount > 0 else "sell",
            "token_amount": amount,
            "sol_amount": quote,
            "price": price,
        })
    return fills


def _wallet_window(coins: list[dict]) -> tuple[int, int]:
    times = [ts for coin in coins for ts in (coin.get("buy_unix") or [])]
    if not times:
        now = unix_now()
        return now - LOOKBACK_SEC, now
    return min(times) - LOOKBACK_SEC, min(max(times) + HOLD_WINDOW_SEC, unix_now())


def _native_sol(tx: dict, address: str) -> tuple[float, float]:
    keys = _account_keys(tx)
    meta = tx.get("meta") or {}
    if address not in keys:
        return 0.0, 0.0
    index = keys.index(address)
    pre = meta.get("preBalances") or []
    post = meta.get("postBalances") or []
    before = float(pre[index]) / LAMPORTS_PER_SOL if index < len(pre) else 0.0
    after = float(post[index]) / LAMPORTS_PER_SOL if index < len(post) else 0.0
    return before, after


def _account_keys(tx: dict) -> list[str]:
    keys = ((tx.get("transaction") or {}).get("message") or {}).get("accountKeys") or []
    out = []
    for key in keys:
        if isinstance(key, dict):
            out.append(str(key.get("pubkey") or ""))
        else:
            out.append(str(key))
    return out


def _ui_amount(row: dict) -> float:
    amount = (row.get("uiTokenAmount") or {}).get("uiAmount")
    value = to_float(amount)
    return 0.0 if value is None else value


def _upsert_universe_row(row: dict) -> None:
    mint = row.get("address")
    if not mint:
        return
    with _UNIVERSE_LOCK:
        universe = load_universe()
        for index, existing in enumerate(universe):
            if existing.get("address") == mint:
                universe[index] = row
                break
        else:
            universe.append(row)
        universe.sort(key=lambda item: (item.get("buy_unix") or [0])[0])
        _write_json(UNIVERSE_PATH, universe)


def _reuse_pool(cached: dict | None, prev: dict) -> dict:
    market = (cached or {}).get("market") or prev.get("market") or prev.get("pool")
    if not market:
        return {}
    return {
        "pool": prev.get("pool") or market,
        "pool_name": prev.get("pool_name"),
        "pool_created_at": prev.get("pool_created_at"),
        "reserve_in_usd": prev.get("reserve_in_usd"),
        "base": prev.get("base"),
        "quote": prev.get("quote"),
        "token_side": prev.get("token_side") or (cached or {}).get("token_side") or "base",
        "market": market,
        "dex": prev.get("dex"),
    }


def _merge_candles(old: list[dict], new: list[dict]) -> list[dict]:
    by_time: dict[int, dict] = {}
    for row in old + new:
        stamp = int(row.get("unix_time") or 0)
        if stamp:
            by_time[stamp] = row
    return [by_time[key] for key in sorted(by_time)]


def load_universe() -> list[dict]:
    data = _read_json(UNIVERSE_PATH, [])
    return data if isinstance(data, list) else []


def load_cached_ohlcv(mint: str) -> dict | None:
    data = _read_json(_ohlcv_path(mint), None)
    return data if isinstance(data, dict) else None


def load_wallet_fills() -> list[dict]:
    data = _read_json(WALLET_FILLS_PATH, {})
    if isinstance(data, dict):
        return list(data.get("fills") or [])
    if isinstance(data, list):
        return data
    return []


def _ohlcv_path(mint: str) -> Path:
    return OHLCV_DIR / f"{mint}_{CANDLE_INTERVAL_SEC // 60}m.json"


def _as_list(value) -> list:
    if isinstance(value, list):
        return [item for item in value if item]
    if value is None or value == "":
        return []
    return [value]


def _first(value):
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    tmp.replace(path)
