"""JSON payloads for the OHLC curve dashboard."""

from src.analysis.structure import analyze_structure
from src.storage.wallet_trades import first_wallet_entry
from src.backtest.stats import dashboard_stats, me_marks, mint_stats
from src.integrations.birdeye import export_mint_ohlc
from src.storage.ohlc import default_wallet, list_ohlc_tokens, list_wallets, ohlc_curve, safe_id


def ohlc_tokens_payload(wallet: str | None = None, *, scoped: bool = False) -> dict:
    selected = safe_id(wallet) if wallet else None
    if scoped and selected is None:
        selected = default_wallet()
    tokens = [
        {
            "address": token["address"],
            "wallet": token["wallet"],
            "wallets": token["wallets"],
            "name": token.get("name"),
            "symbol": token.get("symbol"),
            "interval": token.get("interval"),
            "source": token.get("source"),
            "creation_time": token.get("creation_time"),
            "age_seconds": token.get("age_seconds"),
            "time_from": token.get("time_from"),
            "time_to": token.get("time_to"),
            "exported_at": token.get("exported_at"),
            "first": token.get("first"),
            "last": token.get("last"),
            "change_pct": token.get("change_pct"),
        }
        for token in list_ohlc_tokens(selected)
    ]
    wallets = list_wallets()
    by_mint = mint_stats(selected)
    for token in tokens:
        token["backtest"] = by_mint.get(token["address"]) or {
            "realized_pnl": 0.0,
            "unrealized_pnl": 0.0,
            "total_pnl": 0.0,
            "wins": 0,
            "losses": 0,
            "trades": 0,
            "fees_total": 0.0,
        }
    return {
        "tokens": tokens,
        "wallets": wallets,
        "wallet": selected,
        "summary": {
            "token_count": len(tokens),
            "wallet_count": len(wallets),
            "backtest": dashboard_stats(selected),
        },
    }


def ohlc_curve_payload(
    address: str,
    wallet: str | None = None,
    interval: str = "1m",
    time_from: int | None = None,
    time_to: int | None = None,
) -> dict | None:
    payload = ohlc_curve(address, wallet, interval, time_from, time_to)
    if payload is not None:
        entry = first_wallet_entry(payload["wallet"], payload["address"])
        points = payload.get("points") or []
        full_from, full_to = payload.get("full_from"), payload.get("full_to")
        # Include earlier history when the default 8,000-bar cap hides the entry.
        if (time_from is None and time_to is None and entry and points
                and full_from is not None and full_to is not None
                and full_from <= entry["t"] < points[0]["t"]):
            expanded = ohlc_curve(
                address, payload["wallet"], interval, full_from, full_to
            )
            if expanded is not None and expanded.get("points"):
                payload = expanded
        payload["target_wallet_first_entry"] = entry
        payload["structure"] = analyze_structure(payload.get("points") or [])
        payload["backtest"] = dashboard_stats(safe_id(wallet), safe_id(address))
        payload["me"] = me_marks(safe_id(wallet), safe_id(address))
    return payload


def refresh_ohlc_payload(
    address: str,
    wallet: str | None = None,
    interval: str | None = None,
) -> dict:
    mint = safe_id(address)
    owner = safe_id(wallet) or default_wallet()
    if not mint:
        raise ValueError("invalid mint")
    if not owner:
        raise ValueError("invalid wallet")
    row = export_mint_ohlc(owner, mint, interval=interval)
    return {
        "ok": True,
        "address": mint,
        "wallet": owner,
        "candles": row.get("candles") or 0,
        "added": row.get("added") or 0,
        "resumed": bool(row.get("resumed")),
        "time_from": row.get("time_from"),
        "time_to": row.get("time_to"),
    }
