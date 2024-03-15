from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from .. import Bot
    from discord import Interaction


@app_commands.default_permissions()
@app_commands.guild_only()
class Template(commands.GroupCog, name="template"):

    def __init__(self, bot: Bot):
        self.bot = bot
        self.logger = self.bot.log_handler.getChild(self.qualified_name)

    async def cog_load(self) -> None:
        self.logger.info(f"{self.qualified_name} cog loaded")

    async def cog_unload(self) -> None:
        self.logger.info(f"{self.qualified_name} cog unloaded")

    @app_commands.command(name="template")
    async def template(self, interaction: Interaction[Bot]): ...


async def setup(bot):
    await bot.add_cog(Template(bot))
