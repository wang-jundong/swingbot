"""Native SOL and SPL token transfer helpers."""

from __future__ import annotations

from typing import Optional

from solders.instruction import Instruction
from solders.pubkey import Pubkey
from solders.system_program import TransferParams, transfer
from spl.token.instructions import (
    create_associated_token_account,
    get_associated_token_address,
    transfer as spl_transfer,
)
from spl.token.models import TransferParams as SplTransferParams

from src.config.solana import LAMPORTS_PER_SOL
from src.dex.solana.common.spl import (
    account_exists,
    get_mint_token_program,
    get_token_decimals,
    human_to_raw,
)
from src.dex.solana.common.transactions import helius_tip_instruction, sign_and_send_instructions
from src.dex.solana.core.connection import get_rpc_and_keypair
from src.storage.coins import get_coin_by_symbol
from src.utils.log_util import get_dex_logger

logger = get_dex_logger()


def _build_token_transfer_instructions(
    rpc_url: str,
    payer: str,
    recipient: str,
    mint: str,
    amount_raw: int,
    token_program: str,
) -> list[Instruction]:
    """Build SPL transfer instructions, creating the recipient ATA if needed."""
    token_program_id = Pubkey.from_string(token_program)
    mint_pubkey = Pubkey.from_string(mint)
    payer_pubkey = Pubkey.from_string(payer)
    recipient_pubkey = Pubkey.from_string(recipient)

    source = get_associated_token_address(payer_pubkey, mint_pubkey, token_program_id)
    if not account_exists(rpc_url, str(source)):
        raise RuntimeError("sender has no token account for this mint")

    destination = get_associated_token_address(
        recipient_pubkey, mint_pubkey, token_program_id
    )
    instructions: list[Instruction] = []
    if not account_exists(rpc_url, str(destination)):
        instructions.append(
            create_associated_token_account(
                payer_pubkey, recipient_pubkey, mint_pubkey, token_program_id
            )
        )

    instructions.append(
        spl_transfer(
            SplTransferParams(
                program_id=token_program_id,
                source=source,
                dest=destination,
                owner=payer_pubkey,
                amount=amount_raw,
            )
        )
    )
    return instructions


def send_native_sol(amount_sol_human: float, recipient: str) -> Optional[str]:
    """Send native SOL from the DEX wallet."""
    if amount_sol_human <= 0:
        raise ValueError("amount must be positive")

    lamports = int(amount_sol_human * LAMPORTS_PER_SOL)
    if lamports <= 0:
        raise ValueError("amount is too small")

    conn = get_rpc_and_keypair()
    if not conn:
        return None
    rpc_url, keypair = conn

    instructions = [
        transfer(
            TransferParams(
                from_pubkey=keypair.pubkey(),
                to_pubkey=Pubkey.from_string(recipient),
                lamports=lamports,
            )
        )
    ]
    instructions.append(helius_tip_instruction(keypair.pubkey()))
    signature, success = sign_and_send_instructions(rpc_url, keypair, instructions)
    if success and signature:
        logger.info("SOL send: %s", signature)
    return signature if success else None


def send_token(symbol: str, amount_human: float, recipient: str) -> Optional[str]:
    """Send an SPL memecoin from the DEX wallet by symbol."""
    if amount_human <= 0:
        raise ValueError("amount must be positive")

    conn = get_rpc_and_keypair()
    if not conn:
        return None
    rpc_url, keypair = conn

    coin = get_coin_by_symbol(symbol)
    if not coin:
        logger.error("unknown token: %s", symbol)
        return None

    mint = coin["address"]
    decimals = coin.get("decimals")
    if decimals is None:
        decimals = get_token_decimals(rpc_url, mint)

    token_program = get_mint_token_program(rpc_url, mint)

    instructions = _build_token_transfer_instructions(
        rpc_url,
        str(keypair.pubkey()),
        recipient,
        mint,
        human_to_raw(amount_human, int(decimals)),
        token_program,
    )
    instructions.append(helius_tip_instruction(keypair.pubkey()))
    signature, success = sign_and_send_instructions(rpc_url, keypair, instructions)
    if success and signature:
        logger.info("%s send: %s", symbol, signature)
    return signature if success else None
