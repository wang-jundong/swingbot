def normalize_coin(entry: dict) -> dict:
    """Normalize a COIN_INFO entry."""
    out = dict(entry)
    out.pop("status", None)
    return out
