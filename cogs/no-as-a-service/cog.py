import discord
from discord import app_commands, Interaction
from discord.ext import commands

from WorstBot import WorstBot
from modules import EmbedGen

from . import Routes, PORT


@app_commands.guild_only()
class NoAsAService(commands.Cog, name="no-as-a-service"):
    def __init__(self, bot: WorstBot):
        super().__init__()
        self.bot = bot
        self.logger = self.bot.logger.getChild(self.qualified_name)

    async def cog_load(self) -> None:
        self.logger.info(f"{self.qualified_name} cog loaded")

    async def cog_unload(self) -> None:
        self.logger.info(f"{self.qualified_name} cog unloaded")

    @app_commands.command(name="no")
    async def no(self, interaction: Interaction[WorstBot]):
        await interaction.response.defer()
        resp = None
        try:
            resp = await self.bot.get(url=f"http://{Routes.primary.value}:{PORT}/no")
        except:
            try:
                resp = await self.bot.get(url=f"http://{Routes.secondary.value}:{PORT}/no")
            except:
                pass
        if resp is None:
            embed = EmbedGen.SimpleEmbed(
                text="Both No-as-a-Service endpoints are unreachable.", colour=discord.Colour.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        embed = EmbedGen.SimpleEmbed(text=resp.get("reason", ""), colour=discord.Colour.green())
        await interaction.followup.send(embed=embed)
