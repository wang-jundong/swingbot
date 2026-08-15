from math import floor, log10


def to_float(value: object) -> float | None:
    """Safely cast value to float, returning None on invalid input."""
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def format_decimal(val: float, digits: int = 4) -> str:
    """Format float with 4 non-zero decimals, e.g. 9.67e-9 -> 0.000000009678."""
    if val == 0:
        return "0.0000"
    if val >= 1:
        return f"{val:.4f}"
    decimals = max(4, -int(floor(log10(abs(val)))) - 1 + digits)
    return f"{val:.{decimals}f}"

