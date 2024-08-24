from __future__ import annotations

from typing import TYPE_CHECKING

from ...core._types import LRU
from .constants import (
    BASE_RATE,
    CACHE_SIZE,
    CONVERSION_MAX,
    CONVERSION_MIN,
    CONVERSION_WEIGHTS,
    LEADERBOARD_SIZE,
    PAGE_SIZE,
)
from .enums import Transactions
from .wealth import Wealth

if TYPE_CHECKING:
    from typing import Any, Callable, Coroutine, TypeAlias

    from discord import Guild, Member

    from WorstBot import Bot

    Currency: TypeAlias = float | int

__all__ = (
    "BASE_RATE",
    "CONVERSION_MAX",
    "CONVERSION_MIN",
    "CONVERSION_WEIGHTS",
    "LEADERBOARD_SIZE",
    "PAGE_SIZE",
    "Transactions",
    "get_wealth",
)


_cache: dict[Guild, LRU[Wealth]] = {}

with open("WorstBot/extensions/economy/wealth.sql", "r") as f:
    fetch_wealth_sql = f.read()


async def fetch_wealth_info(bot: Bot, member: Member) -> dict[str, Any]:
    row = await bot.pool.fetchrow(fetch_wealth_sql, (member.guild.id, member.id))

    if row:
        return dict(row)
    else:
        return {}


async def get_wealth(bot: Bot) -> Callable[[Member], Coroutine[Any, Any, Wealth]]:
    logger = bot.log_handler.getChild(__name__)

    async def inner_func(member: Member) -> Wealth:
        guild = member.guild
        if not _cache.get(guild):
            logger.debug(f"Cache for {guild} created")
            _cache[guild] = LRU(max_size=CACHE_SIZE)

        if wealth := _cache[guild].get(member):
            logger.debug(f"Wealth for {member} found in cache")
            return wealth

        data = await fetch_wealth_info(bot, member)
        if data:
            logger.debug(f"Wealth for {member} found in database")
            wealth = Wealth(
                member,
                wallet=data["wallet_balance"],
                bank=data["bank_balance"],
                tokens=data["ascended_balance"],
                multiplier=data["conversion_rate"],
            )
            _cache[guild].set(wealth)
            return wealth

        wealth = Wealth(member)
        _cache[guild].set(wealth)
        logger.debug(f"Wealth for {member} created and added to cache")
        return wealth

    return inner_func


async def deposit(bot: Bot, wealth: Wealth, amount: Currency) -> Wealth:
    await bot.pool.execute(
        "INSERT INTO economy(member, transaction, amount) VALUES($1, $2, $3)",
        (wealth.member.guild.id, wealth.member.id),
        Transactions.deposit,
        amount,
    )
    wealth._wallet -= amount
    wealth._bank += amount
    return wealth


async def withdraw(bot: Bot, wealth: Wealth, amount: Currency) -> Wealth:
    await bot.pool.execute(
        "INSERT INTO economy(member, transaction, amount) VALUES($1, $2, $3)",
        (wealth.member.guild.id, wealth.member.id),
        Transactions.withdraw,
        amount,
    )
    wealth._wallet += amount
    wealth._bank -= amount
    return wealth


async def transfer(bot: Bot, wealth: Wealth, target: Wealth, amount: Currency) -> tuple[Wealth, Wealth]:
    await bot.pool.execute(
        "INSERT INTO economy(member, transaction, amount, recipient) VALUES($1, $2, $3, $4) RETURNING recipient",
        (wealth.member.guild.id, wealth.member.id),
        Transactions.give,
        amount,
        (target.member.guild.id, target.member.id),
    )
    await bot.pool.execute(
        "INSERT INTO economy(member, transaction, amount, recipient, transaction_id) VALUES($1, $2, $3, $4, $5)",
        (target.member.guild.id, target.member.id),
        Transactions.receive,
        amount,
        (wealth.member.guild.id, wealth.member.id),
    )
    wealth._wallet -= amount
    target._wallet += amount
    return wealth, target


async def ascend(bot: Bot, wealth: Wealth, amount: Currency, rate: float) -> Wealth:
    await bot.pool.execute(
        "INSERT INTO economy(member, transaction, amount) VALUES($1, $2, $3)",
        (wealth.member.guild.id, wealth.member.id),
        Transactions.ascend,
        amount * rate,
    )
    wealth._wallet -= amount
    wealth._tokens += amount * rate
    return wealth


async def payout(bot: Bot, wealth: Wealth, event: Transactions, amount: Currency) -> None:
    await bot.pool.execute(
        "INSERT INTO economy(member, transaction, amount) VALUES($1, $2, $3)",
        (wealth.member.guild.id, wealth.member.id),
        event,
        amount,
    )
