from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.app_commands import Range
from discord.ext import commands

from ._enums import Games
from ._game_manager import GameManager

if TYPE_CHECKING:
    from discord import Guild, Interaction

    from WorstBot import Bot


@app_commands.default_permissions()
@app_commands.guild_only()
class Gambling(commands.GroupCog, name="gambling"):

    def __init__(self, bot: Bot):
        self.bot = bot
        self.logger = self.bot.log_handler.getChild(self.qualified_name)
        self.games: dict[Guild, dict[Games, GameManager]] = {}

    async def cog_load(self) -> None:
        self.logger.info(f"{self.qualified_name} cog loaded")

    async def cog_unload(self) -> None:
        self.logger.info(f"{self.qualified_name} cog unloaded")

    @app_commands.command(name="start")
    async def start_lobby(self, interaction: Interaction[Bot], game: Games, bet: Range[float, 0]): ...


async def setup(bot: Bot) -> None:
    await bot.add_cog(Gambling(bot))
