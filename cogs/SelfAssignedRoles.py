import discord
from discord import app_commands, Interaction
from discord.ext import commands


class BaseEvents(commands.GroupCog, name = "template"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("SelfAssignableRoles Cog online")

async def setup(bot):
    await bot.add_cog(BaseEvents(bot))
