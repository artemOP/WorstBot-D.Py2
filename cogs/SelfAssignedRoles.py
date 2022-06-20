import discord
from discord import User, app_commands, Interaction
from discord.ext import commands
from discord.app_commands import Choice

class SelfAssignableRoles(commands.GroupCog, name = "giveme"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.execute("CREATE TABLE IF NOT EXISTS selfroles(guild BIGINT NOT NULL, role BIGINT PRIMARY KEY)")
        print("SelfAssignableRoles Cog online")

    @app_commands.command(name = "role")
    async def ToggleRole(self, interaction: Interaction, role: int):
        ...

    @ToggleRole.autocomplete("role")
    async def ToggleRoleAutocomplete(self, interaction:Interaction, current) -> [Choice]:
        roles = await self.bot.fetch("SELECT roles FROM selfroles WHERE guild = $1", interaction.guild_id)
        print(roles)

async def setup(bot):
    await bot.add_cog(SelfAssignableRoles(bot))
