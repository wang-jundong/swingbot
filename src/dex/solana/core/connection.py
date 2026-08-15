"""Solana RPC and wallet connection."""

from __future__ import annotations

import json
import time
from typing import Optional

from solders.keypair import Keypair

from src.config.bindings.binding import BINDINGS
from src.config.solana import RPC_RECONNECT_ATTEMPTS, RPC_RECONNECT_DELAY_SEC
from src.dex.solana.common.transactions import rpc_request
from src.storage.settings import get_key_id
from src.utils.encrypt_util import decrypt_sig
from src.utils.log_util import get_dex_logger

logger = get_dex_logger()


def get_rpc_url() -> str:
    """RPC endpoint from SOLANA_RPC_URL."""
    return BINDINGS["SOLANA_RPC_URL"].strip()


def load_keypair(private_key: str) -> Keypair:
    """Load a keypair from base58 or JSON byte array."""
    key = private_key.strip()
    if not key:
        raise ValueError("SOLANA_PRIVATE_KEY is empty")

    if key.startswith("["):
        secret = bytes(json.loads(key))
        return Keypair.from_bytes(secret)

    return Keypair.from_base58_string(key)


def get_keypair(key_id: str = "solana") -> Keypair:
    """Keypair from encrypted Solana private key."""
    return load_keypair(decrypt_sig(key_id))


def is_rpc_connected(rpc_url: str) -> bool:
    """Return True when the RPC endpoint responds to getHealth."""
    try:
        result = rpc_request(rpc_url, "getHealth", [])
        return result == "ok"
    except Exception:
        return False


def get_rpc_and_keypair(key_id: str | None = None) -> Optional[tuple[str, Keypair]]:
    """(rpc_url, keypair) or None if RPC/wallet unavailable. Retries RPC connection."""
    key_id = key_id or get_key_id()
    rpc_url = get_rpc_url()

    for attempt in range(RPC_RECONNECT_ATTEMPTS):
        if is_rpc_connected(rpc_url):
            try:
                return rpc_url, get_keypair(key_id)
            except Exception as exc:
                logger.error("Failed to load Solana keypair: %s", exc)
                return None

        logger.warning(
            "Solana RPC not connected (attempt %d/%d), retrying in %ds",
            attempt + 1,
            RPC_RECONNECT_ATTEMPTS,
            RPC_RECONNECT_DELAY_SEC,
        )
        if attempt < RPC_RECONNECT_ATTEMPTS - 1:
            time.sleep(RPC_RECONNECT_DELAY_SEC)

    logger.error("Solana RPC not connected after %d attempts", RPC_RECONNECT_ATTEMPTS)
    return None
