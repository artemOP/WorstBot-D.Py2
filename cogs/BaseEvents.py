import discord
from discord import app_commands, Interaction
from discord.app_commands import Choice
from discord.ext import commands
from WorstBot import WorstBot, _events

events = [event.name for event in _events]

class BaseEvents(commands.Cog):

    def __init__(self, bot: WorstBot):
        self.bot = bot
        self.logger = self.bot.logger.getChild(self.qualified_name)

    async def cog_load(self) -> None:
        await self.bot.execute(
            """
            CREATE TABLE IF NOT EXISTS 
            events(
            guild BIGINT PRIMARY KEY,
            autorole BOOLEAN DEFAULT TRUE, 
            birthdays BOOLEAN DEFAULT TRUE,
            autoevent BOOLEAN DEFAULT TRUE,
            roles BOOLEAN DEFAULT TRUE, 
            opinion BOOLEAN DEFAULT TRUE,
            calls BOOLEAN DEFAULT TRUE,
            twitch BOOLEAN DEFAULT TRUE,
            textarchive BOOLEAN DEFAULT TRUE,
            usage BOOLEAN DEFAULT TRUE     
            )
            """
        )
        self.logger.info(f"{self.qualified_name} cog loaded")

    async def cog_unload(self) -> None:
        self.logger.info(f"{self.qualified_name} cog unloaded")

    @staticmethod
    def Choices() -> list[Choice[str]]:
        return [app_commands.Choice(name = event, value = event) for event in events]

    @app_commands.command(name = "toggle", description = "toggle automatic events on a server level")
    @app_commands.default_permissions()
    @app_commands.choices(event = Choices())
    @app_commands.guild_only()
    async def toggle(self, interaction: Interaction, event: Choice[str]):
        await interaction.response.defer(ephemeral = True)
        if not await self.bot.fetchval("SELECT EXISTS(SELECT 1 FROM events WHERE guild = $1)", interaction.guild_id):
            await self.on_guild_join(interaction.guild)
        toggle = await self.bot.execute(f"UPDATE events SET {event.name} = NOT {event.name} WHERE guild = $1 RETURNING {event.name}", interaction.guild_id)
        if self.bot._event_toggles.get(interaction.guild_id):
            self.bot._event_toggles.pop(interaction.guild_id)

        await interaction.followup.send(f"{event.name} set to: {toggle}", ephemeral = True)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        await self.bot.execute("INSERT INTO events(guild) VALUES($1)", guild.id)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        await self.bot.execute("DELETE FROM events WHERE guild = $1", guild.id)

async def setup(bot):
    await bot.add_cog(BaseEvents(bot))
