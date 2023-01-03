import discord
from discord import app_commands, Interaction
from discord.ext import commands
from WorstBot import WorstBot

@app_commands.default_permissions()
class Template(commands.GroupCog, name = "template"):

    def __init__(self, bot: WorstBot):
        self.bot = bot

    async def cog_load(self) -> None:
        ...

    async def cog_unload(self) -> None:
        ...

    @commands.Cog.listener()
    async def on_ready(self):
        print("Template cog online")

    @app_commands.command(name = "template")
    async def template(self, interaction: Interaction):
        ...

async def setup(bot):
    await bot.add_cog(Template(bot))
