"""Solana DEX client facade over Jupiter router and SPL helpers."""

from __future__ import annotations

import time
from typing import Optional, Tuple, Union

from src.storage.coins import get_coin_by_symbol
from src.dex.history.recorder import record_buy, record_sell
from src.dex.solana.common.spl import get_token_balance, get_token_decimals
from src.dex.solana.common.transactions import rpc_request
from src.config.solana import LAMPORTS_PER_SOL
from src.dex.solana.core.connection import get_keypair, get_rpc_and_keypair
from src.storage.settings import get_key_id
from src.dex.solana.jupiter import price as jupiter_price
from src.dex.solana.jupiter import router as jupiter_router
from src.utils.log_util import get_dex_logger

logger = get_dex_logger()


class DexClient:
    """Solana DEX facade: buy/sell tokens via Jupiter."""

    def __init__(self) -> None:
        conn = get_rpc_and_keypair()
        if not conn:
            raise RuntimeError(
                "RPC or wallet not available. "
                "Check SOLANA_RPC_URL and SOLANA_PRIVATE_KEY configuration."
            )
        self.rpc_url, _ = conn
        logger.info(
            "Solana DexClient initialized (address=%s)",
            self.keypair.pubkey(),
        )

    @property
    def keypair(self):
        """Active wallet keypair (follows ``settings.json`` mode)."""
        return get_keypair(get_key_id())

    def buy(
        self,
        symbol: str,
        amount_sol_human: float,
        *,
        recipient: Optional[str] = None,
    ) -> Tuple[Optional[str], bool, Optional[float], Optional[float]]:
        """Buy with SOL and return tx result plus SOL balances."""
        owner = str(self.keypair.pubkey())
        balance_before = self.get_native_balance(owner)

        tx_hash, success = jupiter_router.buy(
            symbol,
            amount_sol_human,
            recipient=recipient,
        )

        balance_after: Optional[float] = None
        if tx_hash and success:
            balance_after = self.get_synced_native_balance(owner, balance_before)
            price = self.get_price_native(symbol) or 0.0
            record_buy(symbol, amount_sol_human, tx_hash, price=price)
        return tx_hash, success, balance_before, balance_after

    def sell(
        self,
        symbol: str,
        amount_in_human_or_label: Union[float, str],
        *,
        recipient: Optional[str] = None,
    ) -> Tuple[Optional[str], bool, float, Optional[float], Optional[float]]:
        """Sell for SOL and return tx result, PnL, and SOL balances."""
        recv_addr = recipient or str(self.keypair.pubkey())
        balance_before = self.get_native_balance(recv_addr)

        tx_hash, success = jupiter_router.sell(
            symbol,
            amount_in_human_or_label,
            recipient=recipient,
        )
        pnl = 0.0
        amount_sol = 0.0
        balance_after: Optional[float] = None

        if tx_hash and success:
            balance_after = self.get_synced_native_balance(recv_addr, balance_before)
            diff = (
                (balance_after - balance_before)
                if balance_after is not None and balance_before is not None
                else 0.0
            )
            amount_sol = diff if diff > 0 else 0.0

            price = self.get_price_native(symbol) or 0.0
            pnl = record_sell(
                symbol,
                amount_in_human_or_label,
                tx_hash,
                price=price,
                amount_native_human=amount_sol,
            )
        return tx_hash, success, pnl, balance_before, balance_after

    def get_native_balance(self, address: Optional[str] = None) -> Optional[float]:
        """Native SOL balance in human units (or DEX wallet if address omitted)."""
        owner = address or str(self.keypair.pubkey())
        result = rpc_request(
            self.rpc_url,
            "getBalance",
            [owner, {"commitment": "confirmed"}],
        )
        lamports = result["value"] if isinstance(result, dict) else result
        return float(lamports) / LAMPORTS_PER_SOL

    def get_synced_native_balance(
        self,
        address: str,
        balance_before: Optional[float],
    ) -> Optional[float]:
        """Poll SOL balance briefly to avoid stale reads after a swap."""
        balance_after = self.get_native_balance(address)
        if balance_before is None or balance_after is None:
            return balance_after

        for delay_sec in (0.7, 1.0, 1.5, 2.0):
            if abs(balance_after - balance_before) > 1e-7:
                break
            time.sleep(delay_sec)
            refreshed = self.get_native_balance(address)
            if refreshed is None:
                break
            balance_after = refreshed

        return balance_after

    def get_balance(self, symbol: str, address: Optional[str] = None) -> Optional[float]:
        """Token balance in human units (or DEX wallet if address omitted)."""
        coin = get_coin_by_symbol(symbol)
        if not coin:
            return None
        token_address = coin.get("address")
        if not token_address:
            return None

        owner = address or str(self.keypair.pubkey())
        decimals = coin.get("decimals")
        if decimals is None:
            try:
                decimals = get_token_decimals(self.rpc_url, token_address)
            except Exception as exc:
                logger.error("Failed to fetch decimals for %s: %s", symbol, exc)
                return None
        else:
            decimals = int(decimals)

        bal = get_token_balance(self.rpc_url, owner, token_address, decimals)
        logger.info(
            "DexClient.get_balance(symbol=%s, address=%s) -> %s",
            symbol,
            address,
            bal,
        )
        return bal

    def get_price_native(self, symbol: str) -> Optional[float]:
        """Spot price in native currency (SOL) per 1 token."""
        return jupiter_price.get_price_sol(symbol)
