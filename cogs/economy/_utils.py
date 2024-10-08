from __future__ import annotations
from typing import TYPE_CHECKING, Self
from dataclasses import dataclass
import logging

from discord import Member, Guild

if TYPE_CHECKING:
    from WorstBot import WorstBot

_log = logging.getLogger("economy._utils")


@dataclass
class Wealth:
    member_id: int
    guild_id: int
    wallet: float = 0.0
    bank: float = 0.0
    tokens: float = 0.0
    multiplier: float = 1.0

    def __hash__(self) -> int:
        return hash(self.member_id)

    def __eq__(self, other) -> bool:
        return self.member_id == other.member_id and self.guild_id == other.guild_id

    async def sync(self, bot: WorstBot) -> None:
        _log.debug(
            f"Syncing {self.member_id} {self.guild_id} {self.wallet} {self.bank} {self.tokens} {self.multiplier}"
        )
        await bot.execute(
            "INSERT INTO economy(user_id, guild_id, wallet, bank, tokens, multiplier) VALUES ($1, $2, $3, $4, $5, $6) ON CONFLICT (user_id, guild_id) DO UPDATE SET wallet=excluded.wallet, bank=excluded.bank, tokens=excluded.tokens, multiplier=excluded.multiplier",
            self.member_id,
            self.guild_id,
            self.wallet,
            self.bank,
            self.tokens,
            self.multiplier,
        )

    async def to_bank(self, bot: WorstBot, amount: float) -> Self:
        self.wallet -= amount
        self.bank += amount
        await self.sync(bot)
        return self

    async def to_wallet(self, bot: WorstBot, amount: float) -> Self:
        self.wallet += amount
        self.bank -= amount
        await self.sync(bot)
        return self

    async def to_tokens(self, bot: WorstBot, amount: float, conversion_rate: float) -> Self:
        self.wallet -= amount
        self.tokens += amount * conversion_rate
        await self.sync(bot)
        return self

    async def to_user(self, bot: WorstBot, amount: float, user: Wealth) -> (Self, Wealth):
        self.wallet -= amount
        user.wallet += amount

        await self.sync(bot)
        await user.sync(bot)

        return self, user

    async def reward(self, bot: WorstBot, amount: float, *, use_multiplier: bool = False) -> Self:
        if use_multiplier:
            amount *= self.multiplier
        self.wallet += amount
        await self.sync(bot)
        return self

    async def punish(self, bot: WorstBot, amount: float, *, use_multiplier: bool = False) -> Self:
        if use_multiplier:
            amount *= self.multiplier
        self.wallet -= amount
        await self.sync(bot)
        return self


async def get_wealth(bot: WorstBot, guild: Guild, user: Member) -> Wealth:
    wealth: Wealth
    paired_id = bot.pair(guild.id, user.id)
    if wealth := bot.economy.get(paired_id):
        _log.debug(
            f"{wealth.member_id} cache hit",
        )
        return wealth

    row = await bot.fetchrow(
        "SELECT user_id, guild_id, wallet, bank, tokens, multiplier FROM economy WHERE user_id = $1 AND guild_id = $2",
        user.id,
        guild.id,
    )
    if not row:
        await bot.execute(
            "INSERT INTO economy(user_id, guild_id) VALUES ($1, $2) ON CONFLICT DO NOTHING", user.id, guild.id
        )
        wealth = Wealth(user.id, guild.id)
        _log.debug(
            f"New user: {wealth.member_id}",
        )
    else:
        wealth = Wealth(*row)
        _log.debug(
            f"{wealth.member_id} cache miss",
        )
    bot.economy[paired_id] = wealth

    return wealth
