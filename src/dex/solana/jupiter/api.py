"""Jupiter HTTP API."""

from __future__ import annotations

from typing import Optional

import requests

from src.config.bindings.binding import BINDINGS
from src.config.solana import RPC_REQUEST_TIMEOUT_SEC, SLIPPAGE_BPS


def build_swap(
    taker: str,
    input_address: str,
    output_address: str,
    input_amount: int,
    dexes: Optional[str] = None,
    recipient: Optional[str] = None,
) -> dict:
    """Call Jupiter /swap/v2/build and return the parsed response."""
    url = f"{BINDINGS['JUPITER_BASE_URL'].strip().rstrip('/')}/swap/v2/build"
    params = {
        "inputMint": input_address,
        "outputMint": output_address,
        "amount": str(input_amount),
        "taker": taker,
        "slippageBps": str(SLIPPAGE_BPS),
        "wrapAndUnwrapSol": "true",
    }
    if dexes:
        params["dexes"] = dexes
    if recipient:
        params["nativeDestinationAccount"] = recipient
    headers = {"x-api-key": BINDINGS["JUPITER_API_KEY"].strip()}

    response = requests.get(url, params=params, headers=headers, timeout=RPC_REQUEST_TIMEOUT_SEC)
    response.raise_for_status()
    return response.json()
