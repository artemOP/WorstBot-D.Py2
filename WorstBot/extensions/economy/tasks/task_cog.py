from __future__ import annotations

import random
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from .. import get_wealth, tasks
from . import embeds

if TYPE_CHECKING:
    from discord import Interaction

    from WorstBot import Bot

    from .. import Wealth


class Tasks(commands.Cog):

    def __init__(self, bot: Bot):
        self.bot = bot
        self.logger = self.bot.log_handler.getChild(self.qualified_name)
        self.tasks = (self.keypad_task, self.counting_task, self.tick_task)

    async def cog_load(self) -> None:
        self.get_wealth = await get_wealth(self.bot)
        self.logger.info(f"{self.qualified_name} cog loaded")

    async def cog_unload(self) -> None:
        self.logger.info(f"{self.qualified_name} cog unloaded")

    async def keypad_task(self, interaction: Interaction[Bot], user: Wealth) -> tasks.KeypadTask:
        code = random.sample("123456789", k=9)
        embed = embeds.KeypadTask(code)
        view = tasks.KeypadTask(user, code)
        await interaction.followup.send(view=view, embed=embed)
        view.response = await interaction.original_response()
        return view

    async def counting_task(self, interaction: Interaction[Bot], user: Wealth) -> tasks.KeypadTask:
        code = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
        embed = embeds.CountingTask()
        view = tasks.KeypadTask(user, code)
        await interaction.followup.send(view=view, embed=embed)
        view.response = await interaction.original_response()
        return view

    async def tick_task(self, interaction: Interaction[Bot], user: Wealth) -> tasks.TickTask:
        embed = embeds.TickTask()
        view = tasks.TickTask(user)
        await interaction.followup.send(view=view, embed=embed)
        view.response = await interaction.original_response()
        return view

    @app_commands.command(name="work")
    @app_commands.checks.cooldown(1, 60 * 60, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.guild_only()
    async def work(self, interaction: Interaction[Bot]):
        """Complete a task to earn money

        Args:
            interaction (Interaction[Bot]): _description_
        """
        assert isinstance(interaction.user, discord.Member)
        wealth = await self.get_wealth(interaction.user)

        await random.choice(self.tasks)(interaction, wealth)


async def setup(bot: Bot) -> None:
    await bot.add_cog(Tasks(bot))
