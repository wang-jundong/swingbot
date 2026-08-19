"""SPL token read helpers."""

from __future__ import annotations

from typing import Union

from spl.token.constants import TOKEN_2022_PROGRAM_ID, TOKEN_PROGRAM_ID

from src.dex.solana.common.transactions import rpc_request


def account_exists(rpc_url: str, address: str) -> bool:
    """Return True when an on-chain account exists."""
    result = rpc_request(
        rpc_url,
        "getAccountInfo",
        [address, {"encoding": "base64"}],
    )
    return result.get("value") is not None


def get_mint_token_program(rpc_url: str, mint_address: str) -> str:
    """Return the token program that owns a mint (classic SPL or Token-2022)."""
    result = rpc_request(
        rpc_url,
        "getAccountInfo",
        [mint_address, {"encoding": "base64"}],
    )
    value = result.get("value")
    if not value:
        raise RuntimeError(f"mint account not found: {mint_address}")

    owner = value.get("owner")
    if owner not in (str(TOKEN_PROGRAM_ID), str(TOKEN_2022_PROGRAM_ID)):
        raise RuntimeError(
            f"unsupported token program for mint {mint_address}: {owner}"
        )
    return owner


def get_token_decimals(rpc_url: str, address: str) -> int:
    """SPL token decimals."""
    result = rpc_request(rpc_url, "getTokenSupply", [address])
    value = result.get("value") or {}
    decimals = value.get("decimals")
    if decimals is None:
        raise RuntimeError(f"could not read decimals for address {address}")
    return int(decimals)


def human_to_raw(amount_human: float, decimals: int) -> int:
    """Human amount → raw."""
    if not amount_human or amount_human <= 0 or amount_human != amount_human:
        raise ValueError("token amount must be positive")
    raw = int(amount_human * (10**decimals))
    if raw <= 0 or raw > 2**64 - 1:
        raise ValueError("token amount is out of supported range")
    return raw


def raw_to_ui(raw: Union[str, int], decimals: int) -> float:
    """Raw amount → human units."""
    return float(raw) / (10**decimals)


def get_token_balance_raw(rpc_url: str, owner: str, address: str) -> int:
    """SPL token balance (raw) for token address at owner."""
    result = rpc_request(
        rpc_url,
        "getTokenAccountsByOwner",
        [
            owner,
            {"mint": address},
            {"encoding": "jsonParsed", "commitment": "confirmed"},
        ],
    )
    accounts = result.get("value") or []
    total_raw = 0
    for account in accounts:
        amount = (
            account.get("account", {})
            .get("data", {})
            .get("parsed", {})
            .get("info", {})
            .get("tokenAmount", {})
            .get("amount", "0")
        )
        total_raw += int(amount)
    return total_raw


def get_token_balance(rpc_url: str, owner: str, address: str, decimals: int) -> float:
    """SPL token balance (human units)."""
    return raw_to_ui(get_token_balance_raw(rpc_url, owner, address), decimals)


def get_owner_token_balances(rpc_url: str, owner: str) -> dict[str, float]:
    """Mint → human balance for every SPL and Token-2022 account."""
    balances: dict[str, float] = {}
    for program_id in (str(TOKEN_PROGRAM_ID), str(TOKEN_2022_PROGRAM_ID)):
        result = rpc_request(
            rpc_url,
            "getTokenAccountsByOwner",
            [
                owner,
                {"programId": program_id},
                {"encoding": "jsonParsed", "commitment": "confirmed"},
            ],
        )
        for account in result.get("value") or []:
            info = (
                account.get("account", {})
                .get("data", {})
                .get("parsed", {})
                .get("info", {})
            )
            mint = info.get("mint")
            token_amount = info.get("tokenAmount") or {}
            ui_amount = token_amount.get("uiAmount")
            if not mint:
                continue
            amount = float(ui_amount) if ui_amount is not None else 0.0
            balances[mint] = balances.get(mint, 0.0) + amount
    return balances
