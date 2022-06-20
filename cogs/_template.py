import discord
from discord import app_commands, Interaction
from discord.ext import commands


class Template(commands.GroupCog, name = "template"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Template cog online")

    @app_commands.command(name = "Template")
    async def template(self, interaction: Interaction):
        ...

async def setup(bot):
    await bot.add_cog(Template(bot))
