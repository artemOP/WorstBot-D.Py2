import discord
from discord.ext import commands
from discord.ext.commands import Context
from WorstBot import WorstBot
from typing import Literal


class Sync(commands.Cog):
    def __init__(self, bot: WorstBot):
        self.bot = bot
        self.logger = self.bot.logger.getChild(self.qualified_name)

    async def cog_load(self) -> None:
        self.logger.info(f"{self.qualified_name} cog loaded")

    async def cog_unload(self) -> None:
        self.logger.info(f"{self.qualified_name} cog unloaded")

    @commands.command(name="sync", description="Sync command")
    @commands.is_owner()
    async def sync(self, ctx: Context, option: Literal["*", "/", "+", "-"] = "*"):
        """Sync commands with set options

        :param ctx: Context
        :param option:
            *: Global Sync
            /: Clear Global Commands
            +: Local Sync
            -: Clear Local Sync
        """
        async with ctx.typing(ephemeral=True):
            await ctx.message.delete(delay=10)
            match option:
                case "*":
                    await self.bot.tree.sync(guild=None)
                    response_message = "Commands synced globally"
                case "/":
                    self.bot.tree.clear_commands(guild=None)
                    await self.bot.tree.sync(guild=None)
                    response_message = "Global commands removed"

                case "+":
                    self.bot.tree.clear_commands(guild=ctx.guild)
                    self.bot.tree.copy_global_to(guild=ctx.guild)
                    await self.bot.tree.sync(guild=ctx.guild)
                    response_message = "Commands synced locally"

                case "-":
                    self.bot.tree.clear_commands(guild=ctx.guild)
                    await self.bot.tree.sync(guild=ctx.guild)
                    response_message = "Local commands removed"

                case _:
                    response_message = "Invalid option passed"
            await self.bot.prepare_mentions.start()
            return await ctx.send(response_message, delete_after=10)


async def setup(bot):
    await bot.add_cog(Sync(bot))
