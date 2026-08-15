"""Shared helpers for Solana transaction execution."""

from __future__ import annotations

import base64
import time
from typing import Any, Optional, Tuple

import requests
from solders.hash import Hash
from solders.instruction import Instruction
from solders.keypair import Keypair
from solders.message import MessageV0
from solders.pubkey import Pubkey
from solders.system_program import TransferParams, transfer
from solders.transaction import VersionedTransaction

from src.config.bindings.binding import BINDINGS
from src.config.solana import (
    CONFIRM_SIGNATURE_ATTEMPTS,
    CONFIRM_SIGNATURE_DELAY_SEC,
    HELIUS_TIP_ACCOUNT,
    HELIUS_TIP_LAMPORTS,
    RPC_REQUEST_TIMEOUT_SEC,
)
from src.utils.log_util import get_dex_logger

logger = get_dex_logger()

_SEND_TX_OPTS = {
    "encoding": "base64",
    "skipPreflight": True,
    "maxRetries": 0,
}


def helius_tip_instruction(payer: Pubkey) -> Instruction:
    """SOL tip transfer required by Helius Sender."""
    return transfer(
        TransferParams(
            from_pubkey=payer,
            to_pubkey=Pubkey.from_string(HELIUS_TIP_ACCOUNT),
            lamports=HELIUS_TIP_LAMPORTS,
        )
    )


def rpc_request(rpc_url: str, method: str, params: Any) -> dict:
    response = requests.post(
        rpc_url,
        json={
            "jsonrpc": "2.0",
            "id": method,
            "method": method,
            "params": params,
        },
        timeout=RPC_REQUEST_TIMEOUT_SEC,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        message = payload["error"].get("message", payload["error"])
        raise RuntimeError(f"RPC {method} error: {message}")
    if "result" not in payload:
        raise RuntimeError(f"RPC {method} response missing result")
    return payload["result"]


def sign_and_send_instructions(
    rpc_url: str,
    keypair: Keypair,
    instructions: list[Instruction],
) -> Tuple[Optional[str], bool]:
    """Compile, sign, send, and confirm a versioned transaction."""
    blockhash_result = rpc_request(
        rpc_url,
        "getLatestBlockhash",
        [{"commitment": "finalized"}],
    )
    blockhash = blockhash_result.get("value", {}).get("blockhash")
    if not blockhash:
        raise RuntimeError("getLatestBlockhash returned no blockhash")

    message = MessageV0.try_compile(
        keypair.pubkey(),
        instructions,
        [],
        Hash.from_string(blockhash),
    )
    signed_tx = VersionedTransaction(message, [keypair])
    signed_tx_b64 = base64.b64encode(bytes(signed_tx)).decode("ascii")
    return send_and_confirm(rpc_url, signed_tx_b64)


def send_with_helius_sender(signed_tx_b64: str) -> str:
    """Send a signed base64 transaction via Helius sender."""

    response = requests.post(
        BINDINGS["HELIUS_SENDER_URL"].strip(),
        json={
            "jsonrpc": "2.0",
            "id": "swap",
            "method": "sendTransaction",
            "params": [signed_tx_b64, _SEND_TX_OPTS],
        },
        timeout=RPC_REQUEST_TIMEOUT_SEC,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        message = payload["error"].get("message", payload["error"])
        raise RuntimeError(f"RPC sendTransaction error: {message}")
    if "result" not in payload:
        raise RuntimeError("RPC sendTransaction response missing result")
    return payload["result"]


def confirm_signature(
    rpc_url: str,
    signature: str,
    *,
    attempts: int = CONFIRM_SIGNATURE_ATTEMPTS,
) -> None:
    """Wait until a transaction signature is confirmed or finalized."""
    for _ in range(attempts):
        result = rpc_request(
            rpc_url,
            "getSignatureStatuses",
            [[signature], {"searchTransactionHistory": True}],
        )
        statuses = result.get("value") or []
        status = statuses[0] if statuses else None
        if not status:
            time.sleep(CONFIRM_SIGNATURE_DELAY_SEC)
            continue

        if status.get("err") is not None:
            raise RuntimeError(f"transaction failed: {status['err']}")

        confirmation = status.get("confirmationStatus")
        if confirmation in ("confirmed", "finalized"):
            return

        time.sleep(CONFIRM_SIGNATURE_DELAY_SEC)

    raise RuntimeError("transaction confirmation timed out")


def send_and_confirm(
    rpc_url: str,
    signed_tx_b64: str,
) -> Tuple[Optional[str], bool]:
    """Send and confirm a transaction. Returns (signature, success)."""
    try:
        signature = send_with_helius_sender(signed_tx_b64)
        confirm_signature(rpc_url, signature)
        return signature, True
    except Exception as exc:
        logger.error("send_and_confirm failed: %s", exc)
        return None, False
