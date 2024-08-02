from __future__ import annotations

import random
from datetime import time, timezone
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands, tasks

from . import BASE_RATE, CONVERSION_MAX, CONVERSION_MIN, CONVERSION_WEIGHTS, get_wealth

if TYPE_CHECKING:
    from discord import Interaction

    from WorstBot import Bot

    from . import Wealth


@app_commands.default_permissions()
@app_commands.guild_only()
class Economy(commands.GroupCog, name="economy"):

    transfer_group = app_commands.Group(name="transfer", description="Transfer money", guild_only=True)
    gambling_group = app_commands.Group(name="gamble", description="Gamble money", guild_only=True)
    shop_group = ...  # todo: marketplace?

    def __init__(self, bot: Bot):
        self.bot = bot
        self.logger = self.bot.log_handler.getChild(self.qualified_name)

    async def cog_load(self) -> None:
        self.logger.info(f"{self.qualified_name} cog loaded")

        self.conversion_rate = (
            await self.bot.pool.fetchval(
                "SELECT amount FROM economy WHERE transaction = 'CONVERSION_RATE' ORDER BY transaction_timestamp DESC LIMIT 1"
            )
            or BASE_RATE
        )
        self.update_conversion_rate.start()

    async def cog_unload(self) -> None:
        self.logger.info(f"{self.qualified_name} cog unloaded")

    @tasks.loop(time=time(1, 0, tzinfo=timezone.utc))
    async def update_conversion_rate(self):
        choice = random.choices(CONVERSION_WEIGHTS.keys(), CONVERSION_WEIGHTS.values())[0]
        match choice:
            case CONVERSION_WEIGHTS.crash:
                self.conversion_rate = CONVERSION_MIN
            case CONVERSION_WEIGHTS.decrease:
                self.conversion_rate = max(self.conversion_rate - random.uniform(0.01, 0.05), CONVERSION_MAX)
            case CONVERSION_WEIGHTS.increase:
                self.conversion_rate = min(self.conversion_rate + random.uniform(0.01, 0.05), CONVERSION_MAX)
            case CONVERSION_WEIGHTS.boom:
                self.conversion_rate = CONVERSION_MAX

        await self.bot.pool.execute(
            "INSERT INTO economy(transaction, amount) VALUES('CONVERSION_RATE', $1)", self.conversion_rate
        )
        self.logger.debug(f"Conversion rate updated to {self.conversion_rate:.2%}")

    @update_conversion_rate.before_loop
    async def before_read(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="test1")
    async def template(self, interaction: Interaction[Bot]): ...


async def setup(bot: Bot) -> None:
    await bot.add_cog(Economy(bot))
