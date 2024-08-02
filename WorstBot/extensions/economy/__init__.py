from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ...core._types import LRU
from .constants import BASE_RATE, CONVERSION_MAX, CONVERSION_MIN
from .enums import CONVERSION_WEIGHTS
from .wealth import Wealth

if TYPE_CHECKING:
    from discord import Guild, Member

    from WorstBot import Bot

__all__ = ("BASE_RATE", "CONVERSION_MAX", "CONVERSION_MIN", "CONVERSION_WEIGHTS", "Wealth")


_cache: dict[Guild, LRU[Wealth]] = {}


async def fetch_wealth_info(bot: Bot) -> dict[str, Any]:
    row = await bot.pool.fetchrow("")

    if row:
        return dict(row)
    else:
        return {}


async def get_wealth(bot: Bot):
    async def inner_func(member: Member):
        guild = member.guild
        if wealth := _cache[guild].get(member):
            return wealth

    return inner_func
