"""OHLC backtest execution assumptions."""

from src.config.birdeye import OHLC_INTERVAL

INTERVAL = OHLC_INTERVAL
POSITION_SIZE_SOL = 0.1
BUY_SLIPPAGE = 0.01
SELL_SLIPPAGE = 0.01
FEE_SOL = 0.0001
FLATTEN_EOT = True
MAX_MINTS = 0
MAX_BUYS = 0
STRATEGY = "none"


def as_dict() -> dict:
    return {
        "INTERVAL": INTERVAL,
        "POSITION_SIZE_SOL": POSITION_SIZE_SOL,
        "BUY_SLIPPAGE": BUY_SLIPPAGE,
        "SELL_SLIPPAGE": SELL_SLIPPAGE,
        "FEE_SOL": FEE_SOL,
        "FLATTEN_EOT": FLATTEN_EOT,
        "MAX_MINTS": MAX_MINTS,
        "MAX_BUYS": MAX_BUYS,
        "STRATEGY": STRATEGY,
    }
