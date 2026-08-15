"""Jupiter swap execution: build response -> sign -> send -> confirm."""

from __future__ import annotations

import base64
from typing import Optional

from solders.address_lookup_table_account import AddressLookupTableAccount
from solders.hash import Hash
from solders.instruction import AccountMeta, Instruction
from solders.keypair import Keypair
from solders.message import MessageV0
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction

from src.dex.solana.common.spl import raw_to_ui
from src.dex.solana.common.transactions import helius_tip_instruction, send_and_confirm
from src.dex.solana.jupiter.api import build_swap


def execute_swap(
    rpc_url: str,
    keypair: Keypair,
    input_address: str,
    output_address: str,
    input_amount: int,
    output_decimals: int,
    dexes: Optional[str] = None,
    recipient: Optional[str] = None,
) -> tuple[str, float]:
    """Build, sign, send, and confirm a Jupiter swap. Returns (signature, quoted_out_ui)."""
    owner = str(keypair.pubkey())
    build = build_swap(
        owner,
        input_address,
        output_address,
        input_amount,
        dexes=dexes,
        recipient=recipient,
    )
    quoted_out = raw_to_ui(build.get("outAmount", "0"), output_decimals)

    instructions = _instructions_from_build(build)
    instructions.append(helius_tip_instruction(keypair.pubkey()))

    lookup_tables = _lookup_table_accounts(build)
    blockhash = _blockhash_from_build(build)
    message = MessageV0.try_compile(
        keypair.pubkey(),
        instructions,
        lookup_tables,
        blockhash,
    )
    signed_tx = VersionedTransaction(message, [keypair])
    signed_tx_b64 = base64.b64encode(bytes(signed_tx)).decode("ascii")

    signature, success = send_and_confirm(rpc_url, signed_tx_b64)
    if not success or not signature:
        raise RuntimeError("Jupiter swap transaction failed")
    return signature, quoted_out


def _instructions_from_build(build: dict) -> list[Instruction]:
    instructions: list[Instruction] = []
    for key in ("setupInstructions", "otherInstructions"):
        for item in build.get(key) or []:
            instructions.append(_api_instruction_to_solders(item))
    instructions.append(_api_instruction_to_solders(build["swapInstruction"]))
    cleanup = build.get("cleanupInstruction")
    if cleanup:
        instructions.append(_api_instruction_to_solders(cleanup))
    return instructions


def _api_instruction_to_solders(item: dict) -> Instruction:
    accounts = [
        AccountMeta(
            _parse_pubkey(account["pubkey"]),
            account.get("isSigner", False),
            account.get("isWritable", False),
        )
        for account in item.get("accounts") or []
    ]
    data = base64.b64decode(item["data"])
    return Instruction(_parse_pubkey(item["programId"]), data, accounts)


def _lookup_table_accounts(build: dict) -> list[AddressLookupTableAccount]:
    tables = build.get("addressesByLookupTableAddress") or {}
    lookup_accounts: list[AddressLookupTableAccount] = []
    for key, addresses in tables.items():
        lookup_accounts.append(
            AddressLookupTableAccount(
                key=_parse_pubkey(key),
                addresses=[_parse_pubkey(address) for address in addresses],
            )
        )
    return lookup_accounts


def _blockhash_from_build(build: dict) -> Hash:
    metadata = build.get("blockhashWithMetadata") or {}
    raw = metadata.get("blockhash")
    if isinstance(raw, list):
        return Hash.from_bytes(bytes(raw))
    if isinstance(raw, str):
        return Hash.from_string(raw)
    raise RuntimeError("Jupiter /build blockhash missing or invalid")


def _parse_pubkey(value: str) -> Pubkey:
    return Pubkey.from_string(value)

