import discord
from discord import app_commands, Interaction
from discord.ext import commands


class Template(commands.GroupCog, name = "template"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        ...

async def setup(bot):
    await bot.add_cog(Template(bot))
