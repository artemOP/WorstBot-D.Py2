import discord
from discord import app_commands, Interaction
from discord.ext import commands
from WorstBot import WorstBot
from modules import RoleManipulation

@app_commands.default_permissions()
class ToggleRoles(commands.Cog):

    def __init__(self, bot: WorstBot):
        self.bot = bot

    async def cog_load(self) -> None:
        await self.bot.execute("CREATE TABLE IF NOT EXISTS toggleroles(id SERIAL PRIMARY KEY, guild BIGINT NOT NULL, role1 BIGINT, role2 BIGINT, UNIQUE(role1, role2))")

    async def cog_unload(self) -> None:
        ...

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.logger.info("ToggleRoles cog online")

    @app_commands.command(name = "toggle-role-setup", description = "Set two roles that can be toggled between, repeating the command will remove the toggle")
    async def Setup(self, interaction: Interaction, role1: discord.Role, role2: discord.Role):
        await interaction.response.defer(ephemeral = True)
        await self.bot.execute("INSERT INTO toggleroles(guild, role1, role2) VALUES($1, $2, $3) ON CONFLICT(role1, role2) DO UPDATE SET guild = 1", interaction.guild_id, role1.id, role2.id)
        await self.bot.execute("DELETE FROM toggleroles WHERE guild = 1")
        await interaction.followup.send(f"{role1.name} <---> {role2.name} Conversion has been added/removed from the setup")

    @app_commands.command(name = "toggle-role", description = "Toggles a user between two roles")
    async def ToggleRole(self, interaction: Interaction, member: discord.Member, toggle: int):
        await interaction.response.defer(ephemeral = True)
        toggle = await self.bot.fetchrow("SELECT role1, role2 FROM toggleroles WHERE id = $1", toggle)
        role1, role2 = interaction.guild.get_role(toggle["role1"]), interaction.guild.get_role(toggle["role2"])
        if role1 in member.roles:
            await RoleManipulation.role_remove(member, role1, "Roles toggled")
            await RoleManipulation.role_add(member, role2, "Roles toggled")
            return await interaction.followup.send(f"{role1.name} -> {role2.name}")
        else:
            await RoleManipulation.role_remove(member, role2, "Roles toggled")
            await RoleManipulation.role_add(member, role1, "Roles toggled")
            return await interaction.followup.send(f"{role2.name} -> {role1.name}")

    @ToggleRole.autocomplete("toggle")
    async def ToggleRoleAutocomplete(self, interaction: Interaction, current) -> list[app_commands.Choice]:
        toggles = await self.bot.fetch("SELECT id, role1, role2 FROM toggleroles WHERE guild = $1", interaction.guild_id)
        return [app_commands.Choice(name = f"{interaction.guild.get_role(role1).name} <---> {interaction.guild.get_role(role2).name}", value = toggle_id) for toggle_id, role1, role2 in toggles]

async def setup(bot):
    await bot.add_cog(ToggleRoles(bot))
