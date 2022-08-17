import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context

class Sync(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Sync cog online")

    @commands.hybrid_command(name = "sync", description = "Sync command")
    @commands.is_owner()
    @app_commands.default_permissions()
    async def sync(self, ctx: Context) -> None:
        await ctx.defer(ephemeral = True)
        guilds = []
        for guild in self.bot.guilds:
            self.bot.tree.clear_commands(guild = guild)
            self.bot.tree.copy_global_to(guild = guild)
            await self.bot.tree.sync(guild = guild)
            guilds.append(guild.name)
        guilds = "\n".join(guilds)
        await ctx.send(f"Successfully synced to:\n{guilds}", ephemeral = True)

    @sync.error
    async def sync_error(self, ctx: Context, error):
        if isinstance(error, commands.NotOwner):
            await ctx.send(str(error), ephemeral = True)
        else:
            print(error)

async def setup(bot):
    await bot.add_cog(Sync(bot))


# alpha = discord.Object(id = 700833272380522496)
# bot.tree.clear_commands(guild = alpha)
# bot.tree.copy_global_to(guild = alpha)
# await bot.tree.sync(guild = alpha)
