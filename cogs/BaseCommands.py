import discord
from discord import app_commands, Interaction
from discord.ext import commands
from datetime import timedelta
import random

class BaseCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self) -> None:
        ...

    async def cog_unload(self) -> None:
        ...

    @commands.Cog.listener()
    async def on_ready(self):
        print("BaseCommands cog online")

    @app_commands.command(name = "ping")
    async def ping(self, interaction: Interaction):
        await interaction.response.send_message(f"Pong!{round(self.bot.latency * 1000)}ms", ephemeral = True)

    @app_commands.command(name = "say")
    @app_commands.default_permissions(manage_messages = True)
    async def say(self, interaction: Interaction, *, arg: str = "what?"):
        await interaction.response.send_message(ephemeral = True, content = "\u200b")
        await interaction.channel.send(content = arg)

    def is_me(self, message: discord.Message) -> bool:
        return not message.author == self.bot.user or message.created_at < discord.utils.utcnow() - timedelta(seconds = 10)

    @app_commands.command(name = "purge")
    @app_commands.default_permissions(manage_messages = True)
    async def purge(self, interaction: Interaction, amount: app_commands.Range[int, 1, 100] = 1):
        await interaction.response.defer(ephemeral = True)
        deleted = await interaction.channel.purge(limit = amount, check = self.is_me, bulk = True if amount > 1 else False, after = interaction.created_at - timedelta(weeks = 2), oldest_first = False)
        await interaction.followup.send(content = f"deleted {len(deleted)} messages")

    @app_commands.command(name = "rtd", description = "role some dice")
    @app_commands.describe(dice="number of dice to roll", sides="number of faces on each die", ephemeral="Set to false to be visible by all")
    async def roll_the_dice(self, interaction: Interaction, dice: int = 1, sides: int = 6, ephemeral: bool = True):
        rolls = [str(random.randint(1, sides)) for _ in range(dice)]
        await interaction.response.send_message(f"You rolled {dice} d{sides}\n\n You rolled: {', '.join(rolls)}", ephemeral=ephemeral)


async def setup(bot):
    await bot.add_cog(BaseCommands(bot))
