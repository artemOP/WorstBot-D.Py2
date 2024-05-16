from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from WorstBot import Bot
    from discord.ext.commands import Context


class SyncOptions(Enum):
    local_add = "+"
    local_remove = "-"
    global_add = "*"
    global_remove = "/"


class Sync(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.logger = self.bot.log_handler.getChild(self.qualified_name)

    async def cog_load(self) -> None:
        self.logger.info(f"{self.qualified_name} cog loaded")

    async def cog_unload(self) -> None:
        self.logger.info(f"{self.qualified_name} cog unloaded")

    @commands.hybrid_command(name="sync", description="Sync command")
    @commands.is_owner()
    @commands.guild_only()
    @app_commands.default_permissions()
    async def sync(self, ctx: Context, option: SyncOptions = SyncOptions.global_add):
        """Sync commands with set options

        :param ctx: Context
        :param option: Sync option
        """
        await ctx.message.delete(delay=10)
        match option:
            case SyncOptions.global_add:
                await self.bot.tree.sync(guild=None)
                response_message = "Commands synced globally"
            case SyncOptions.global_remove:
                self.bot.tree.clear_commands(guild=None)
                await self.bot.tree.sync(guild=None)
                response_message = "Global commands removed"

            case SyncOptions.local_add:
                assert ctx.guild
                self.bot.tree.copy_global_to(guild=ctx.guild)
                await self.bot.tree.sync(guild=ctx.guild)
                response_message = "Commands synced locally"

            case SyncOptions.local_remove:
                self.bot.tree.clear_commands(guild=ctx.guild)
                await self.bot.tree.sync(guild=ctx.guild)
                response_message = "Local commands removed"

            case _:
                response_message = "Invalid option passed"
        return await ctx.send(response_message, delete_after=10)


async def setup(bot: Bot):
    guild = bot.config["discord"]["guild"]
    await bot.add_cog(Sync(bot), guild=discord.Object(id=guild))
