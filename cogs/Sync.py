import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context
from typing import Literal

class Sync(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self) -> None:
        ...

    async def cog_unload(self) -> None:
        ...

    @commands.Cog.listener()
    async def on_ready(self):
        print("Sync cog online")

    @commands.hybrid_command(name = "sync", description = "Sync command")
    @commands.is_owner()
    @app_commands.default_permissions()
    @app_commands.describe(option = "*|/ to add|remove global sync, +|- to add|remove local sync")
    async def sync(self, ctx: Context, option: Literal["*", "/", "+", "-"]) -> discord.Message:
        await ctx.defer(ephemeral = True)
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

    @sync.error
    async def sync_error(self, ctx: Context, error):
        if isinstance(error, commands.NotOwner):
            await ctx.send(str(error), ephemeral = True)
        elif isinstance(error, commands.BadLiteralArgument):
            await ctx.send("Incorrect option passed, please try again")
        else:
            raise error

async def setup(bot):
    await bot.add_cog(Sync(bot))
