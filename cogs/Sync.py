import discord
from discord.ext import commands
from discord.ext.commands import Context
from WorstBot import WorstBot
from typing import Literal

class Sync(commands.Cog):
    def __init__(self, bot: WorstBot):
        self.bot = bot

    async def cog_load(self) -> None:
        ...

    async def cog_unload(self) -> None:
        ...

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.logger.info("Sync cog online")

    @commands.command(name = "sync", description = "Sync command")
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
        async with ctx.typing(ephemeral = True):
            match option:
                case "*":
                    await self.bot.tree.sync(guild = None)
                    return await ctx.send("Commands synced globally")

                case "/":
                    self.bot.tree.clear_commands(guild = None)
                    await self.bot.tree.sync(guild = None)
                    return await ctx.send("Global commands removed")

                case "+":
                    self.bot.tree.clear_commands(guild = ctx.guild)
                    self.bot.tree.copy_global_to(guild = ctx.guild)
                    await self.bot.tree.sync(guild = ctx.guild)
                    return await ctx.send("Commands synced locally")

                case "-":
                    self.bot.tree.clear_commands(guild = ctx.guild)
                    await self.bot.tree.sync(guild = ctx.guild)
                    return await ctx.send("Local commands removed")

                case _:
                    return await ctx.send("Invalid option passed")

async def setup(bot):
    await bot.add_cog(Sync(bot))
