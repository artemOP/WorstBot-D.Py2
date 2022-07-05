import discord
from discord import app_commands, Interaction
from discord.app_commands import Choice
from discord.ext import commands

events = ["autorole", "roles", "opinion", "calls", "textarchive", "twitch"]

class BaseEvents(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.execute(
            """
            CREATE TABLE IF NOT EXISTS 
            events(
            guild BIGINT PRIMARY KEY,
            autorole BOOLEAN DEFAULT TRUE, 
            roles BOOLEAN DEFAULT TRUE, 
            opinion BOOLEAN DEFAULT TRUE,
            calls BOOLEAN DEFAULT TRUE,
            twitch BOOLEAN DEFAULT TRUE,
            textarchive BOOLEAN DEFAULT TRUE      
            )
            """
        )
        print("BaseEvents cog online")

    @staticmethod
    def Choices() -> list[Choice[str]]:
        return [app_commands.Choice(name = event, value = event) for event in events]

    @app_commands.command(name = "toggle", description = "toggle automatic events on a server level")
    @app_commands.default_permissions()
    @app_commands.choices(event = Choices())
    async def toggle(self, interaction: Interaction, event: Choice[str]):
        if not await self.bot.fetchval("SELECT EXISTS(SELECT 1 FROM events WHERE guild = $1)", interaction.guild_id):
            await self.on_guild_join(interaction.guild)
        toggle = await self.bot.execute(f"UPDATE events SET {event.value} = NOT {event.value} WHERE guild = $1 RETURNING {event.value}", interaction.guild_id)
        await interaction.response.send_message(f"{event.value} set to: {toggle}", ephemeral = True)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        await self.bot.execute("INSERT INTO events(guild) VALUES($1)", guild.id)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        await self.bot.execute("DELETE FROM events WHERE guild = $1", guild.id)

async def setup(bot):
    await bot.add_cog(BaseEvents(bot))
