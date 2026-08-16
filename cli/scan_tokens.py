"""CLI: scan tokens via Birdeye Token List V3."""

import sys

from src.integrations.birdeye import scan_tokens


def main() -> int:
    tokens = scan_tokens()
    print(f"matched {len(tokens)}")
    for token in tokens:
        print(_format_token(token))
    return 0


def _format_token(token: dict) -> str:
    age = token.get("pair_age_days")
    age_text = f"{age:.2f}d" if age is not None else "?"
    return (
        f"{token.get('symbol') or '?':<12} "
        f"liq={token.get('liquidity_usd') or 0:,.0f} "
        f"age={age_text} "
        f"holders={token.get('holders')} "
        f"tx24={token.get('txns_h24')} "
        f"range24={_pct(token.get('price_range_24h_pct'))} "
        f"range8={_pct(token.get('price_range_8h_pct'))} "
        f"chg1h={_pct(token.get('price_change_1h_percent'))} "
        f"chg2h={_pct(token.get('price_change_2h_percent'))} "
        f"chg4h={_pct(token.get('price_change_4h_percent'))} "
        f"chg8h={_pct(token.get('price_change_8h_percent'))} "
        f"vs1h={_pct(token.get('price_vs_1h_high_pct'))} "
        f"reason={token.get('filter_reason') or '?'} "
        f"addr={token.get('address')}"
    )


def _pct(value: float | None) -> str:
    return f"{value:.1f}%" if value is not None else "?"


if __name__ == "__main__":
    sys.exit(main())
