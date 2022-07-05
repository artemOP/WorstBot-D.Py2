import discord
from discord import app_commands, Interaction
from discord.ext import commands, tasks


class BirthdayAlert(commands.GroupCog, name = "birthday"):

    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("BirthdayAlert cog online")

    @app_commands.command(name = "add")
    async def BirthdayAdd(self, interaction: Interaction):
        ...

    @app_commands.command(name = "remove")
    async def BirthdayRemove(self, interaction: Interaction):
        ...

    @app_commands.command(name = "list")
    async def BirthdayList(self, interaction: Interaction):
        ...

    @tasks.loop(minutes = 1)
    async def BirthdayCheck(self, interaction: Interaction):
        ...

async def setup(bot):
    await bot.add_cog(BirthdayAlert(bot))
