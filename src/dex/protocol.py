"""Shared DEX client interface for multi-chain trading."""

from __future__ import annotations

from typing import Optional, Protocol, Tuple, Union


class DexClient(Protocol):
    """Contract implemented by chain-specific DEX facades."""

    def buy(
        self,
        symbol: str,
        amount_native_human: float,
        *,
        recipient: Optional[str] = None,
    ) -> Tuple[Optional[str], bool, Optional[float], Optional[float]]: ...

    def sell(
        self,
        symbol: str,
        amount_in_human_or_label: Union[float, str],
        *,
        recipient: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Tuple[Optional[str], bool, float, Optional[float], Optional[float]]: ...

    def get_native_balance(self, address: Optional[str] = None) -> Optional[float]: ...

    def get_synced_native_balance(
        self,
        address: str,
        balance_before: Optional[float],
    ) -> Optional[float]: ...

    def get_balance(self, symbol: str, address: Optional[str] = None) -> Optional[float]: ...

    def get_price_native(self, symbol: str) -> Optional[float]: ...
