import discord
from discord import app_commands, Interaction
from discord.ext import commands


class Admin(commands.GroupCog, name = "admin"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Admin cog online")

    @app_commands.command(name = "template")
    async def template(self, interaction: Interaction):
        ...

async def setup(bot):
    await bot.add_cog(Admin(bot))
