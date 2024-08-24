from __future__ import annotations

from typing import TYPE_CHECKING

from ...core._types import HashableMember

if TYPE_CHECKING:
    from discord import Member


class Wealth(HashableMember):
    __slots__ = ("_member", "_wallet", "_bank", "_tokens", "_multiplier")

    def __init__(
        self,
        member: Member,
        wallet: float = 0,
        bank: float = 0,
        tokens: float = 0,
        multiplier: float = 1,
    ) -> None:
        self._member = member
        self._wallet = wallet
        self._bank = bank
        self._tokens = tokens
        self._multiplier = multiplier

    @property
    def member(self) -> Member:
        return self._member

    @property
    def wallet(self) -> float:
        return self._wallet

    @property
    def bank(self) -> float:
        return self._bank

    @property
    def tokens(self) -> float:
        return self._tokens

    @property
    def multiplier(self) -> float:
        return self._multiplier

    def __repr__(self) -> str:
        return f"<Wealth member={self.member} wallet={self.wallet} bank={self.bank} tokens={self.tokens} multiplier={self.multiplier}>"

    def __str__(self) -> str:
        return f"{self.member} has {self.wallet} in wallet, {self.bank} in bank, {self.tokens} in tokens, and a multiplier of {self.multiplier}"
