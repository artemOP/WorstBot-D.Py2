import discord
from discord import app_commands, Interaction
from discord.ext import commands


class BaseEvents(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.events = ["autorole", "roles", "opinion", "calls", "twitch"]

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
            twitch BOOLEAN DEFAULT TRUE       
            )
            """
        )
        print("BaseEvents cog online")

    @app_commands.command(name = "toggle", description = "toggle automatic events on a server level")
    async def toggle(self, interaction: Interaction, event: str):
        if event not in self.events:
            return
        if not await self.bot.fetchval("SELECT EXISTS(SELECT 1 FROM events WHERE guild = $1)", interaction.guild_id):
            await self.on_guild_join(interaction.guild)
        toggle = await self.bot.execute(f"UPDATE events SET {event} = NOT {event} WHERE guild = $1 RETURNING {event}", interaction.guild_id)
        await interaction.response.send_message(f"{event} set to: {toggle}")

    @toggle.autocomplete("event")
    async def ToggleAutocomplete(self, interaction: Interaction, current):
        if current:
            return [app_commands.Choice(name = event, value = event) for event in self.events if current in event]
        return [app_commands.Choice(name = event, value = event) for event in self.events]

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        await self.bot.execute("INSERT INTO events(guild) VALUES($1)", guild.id)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        await self.bot.execute("DELETE FROM events WHERE guild = $1", guild.id)

async def setup(bot):
    await bot.add_cog(BaseEvents(bot))
