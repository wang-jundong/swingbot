"""Market-structure detection parameters."""

# 1-left / 1-right, confirmed when candle i closes:
# high: High[i-1] >= High[i-2] and High[i-1] > High[i]
# low:  Low[i-1] <= Low[i-2]  and Low[i-1]  < Low[i]
# The mark is printed on the swing candle (i-1) at Close[i-1].
PIVOT_LEFT = 1
PIVOT_RIGHT = 1
ATR_PERIOD = 14
PIVOT_ATR_MULT = 1.0  # Candle-pivot confirmation reversal in ATR units; 0 disables.
KAMA_PIVOT_ATR_MULT = 0.2  # KAMA-pivot confirmation reversal in ATR units; 0 disables.
MIN_PRICE_DISTANCE = 0.1  # Directional move required between accepted pivots.
MIN_BAR_DISTANCE = 30  # Minimum bars from H to L only, for price and KAMA pivots.
KAMA_PERIOD = 10
KAMA_FAST = 2
KAMA_SLOW = 30
KAMA_SLOPE = 3
KAMA_FLAT_ATR = 0.12


def as_dict() -> dict:
    return {
        "PIVOT_LEFT": PIVOT_LEFT,
        "PIVOT_RIGHT": PIVOT_RIGHT,
        "ATR_PERIOD": ATR_PERIOD,
        "PIVOT_ATR_MULT": PIVOT_ATR_MULT,
        "KAMA_PIVOT_ATR_MULT": KAMA_PIVOT_ATR_MULT,
        "MIN_PRICE_DISTANCE": MIN_PRICE_DISTANCE,
        "MIN_BAR_DISTANCE": MIN_BAR_DISTANCE,
        "KAMA_PERIOD": KAMA_PERIOD,
        "KAMA_FAST": KAMA_FAST,
        "KAMA_SLOW": KAMA_SLOW,
        "KAMA_SLOPE": KAMA_SLOPE,
        "KAMA_FLAT_ATR": KAMA_FLAT_ATR,
    }
