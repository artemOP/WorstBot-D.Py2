import discord
from discord import app_commands, Interaction
from discord.ext import commands
from discord.app_commands import Choice, Transform, Transformer

class RoleTransformer(Transformer):

    @classmethod
    async def transform(cls, interaction: Interaction, value: str) -> discord.Role:
        return interaction.guild.get_role(await interaction.client.to_int(value))

    @classmethod
    async def autocomplete(cls, interaction: Interaction, current) -> list[Choice[str]]:
        roleids = await interaction.client.fetch("SELECT role FROM selfroles WHERE guild = $1", interaction.guild_id)
        roles = {role["role"]: interaction.guild.get_role(role["role"]).name for role in roleids}
        if not current:
            return [Choice(name = item[1], value = str(item[0])) for item in roles.items()]
        return [Choice(name = item[1], value = str(item[0])) for item in roles.items() if current in item[1]]

class SelfAssignableRoles(commands.Cog):
    AdminGroup = app_commands.Group(name = "giveme-setup", description = "add or remove self assignable roles", default_permissions = discord.Permissions(administrator = True))
    UserGroup = app_commands.Group(name = "giveme", description = "Toggle a self assignable role")

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.execute("CREATE TABLE IF NOT EXISTS selfroles(guild BIGINT NOT NULL, role BIGINT PRIMARY KEY)")
        print("SelfAssignableRoles Cog online")

    @AdminGroup.command(name = "add")
    async def AddRole(self, interaction: Interaction, role: discord.Role):
        await self.bot.execute("INSERT INTO selfroles(guild, role) VALUES ($1, $2) ON CONFLICT DO NOTHING", interaction.guild_id, role.id)
        await interaction.response.send_message(f"{role.name} added as a self assignable role", ephemeral = True)

    @AdminGroup.command(name = "remove")
    async def RemoveRole(self, interaction: Interaction, role: Transform[discord.Role, RoleTransformer]):
        await self.bot.execute("DELETE FROM selfroles WHERE role = $1", role.id)
        await interaction.response.send_message(f"{role.name} removed as a self assignable role", ephemeral = True)

    @UserGroup.command(name = "role")
    async def ToggleRole(self, interaction: Interaction, role: Transform[discord.Role, RoleTransformer]):
        if not role:
            return
        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            return await interaction.response.send_message(f"You have removed the {role.name} role", ephemeral = True)
        await interaction.user.add_roles(role)
        await interaction.response.send_message(f"You have added the {role.name} role", ephemeral = True)

    @UserGroup.command(name = "list")
    async def ListRole(self, interaction: Interaction):
        roles = await self.bot.fetch("SELECT role FROM selfroles WHERE guild = $1", interaction.guild_id)
        embed = discord.Embed(title = "giveme roles", colour = discord.Colour.random())
        for index, value in enumerate(roles):
            roles[index] = interaction.guild.get_role(value["role"])
        if roles:
            embed.description = "\n\n".join(f"`{role.name}`" for role in roles)
        await interaction.response.send_message(embed = embed, ephemeral = True)


async def setup(bot):
    await bot.add_cog(SelfAssignableRoles(bot))
