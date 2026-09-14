"""JSON payloads for the OHLC curve dashboard."""

from src.analysis.structure import analyze_structure
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
    return {
        "tokens": tokens,
        "wallets": wallets,
        "wallet": selected,
        "summary": {
            "token_count": len(tokens),
            "wallet_count": len(wallets),
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
        payload["structure"] = analyze_structure(payload.get("points") or [])
    return payload
