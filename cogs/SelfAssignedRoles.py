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

class SelfAssignableRoles(commands.GroupCog, name = "giveme", description = "Toggle a self assignable role"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.execute("CREATE TABLE IF NOT EXISTS selfroles(guild BIGINT NOT NULL, role BIGINT PRIMARY KEY)")
        print("SelfAssignableRoles Cog online")

    @app_commands.command(name = "role")
    async def ToggleRole(self, interaction: Interaction, role: Transform[discord.Role, RoleTransformer]):
        if not role:
            return
        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message(f"You have removed the {role.name} role", ephemeral = True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"You have added the {role.name} role", ephemeral = True)

    @app_commands.command(name = "list")
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
