import discord
from discord import app_commands, Interaction
from discord.ext import commands
from discord.app_commands import Choice, Transform, Transformer
from WorstBot import WorstBot
from modules import EmbedGen, Converters, RoleManipulation


class RoleTransformer(Transformer):

    async def transform(self, interaction: Interaction, value: str) -> discord.Role:
        return interaction.guild.get_role(Converters.to_int(value))

    async def autocomplete(self, interaction: Interaction, current) -> list[Choice[str]]:
        roleids = await interaction.client.fetch("SELECT role FROM selfroles WHERE guild = $1", interaction.guild_id)
        roles = {role["role"]: interaction.guild.get_role(role["role"]).name for role in roleids}
        if not current:
            return [Choice(name = item[1], value = str(item[0])) for item in roles.items()]
        return [Choice(name = item[1], value = str(item[0])) for item in roles.items() if current in item[1]]


class SelfAssignableRoles(commands.GroupCog, name = "giveme", description = "Toggle a self assignable role"):
    def __init__(self, bot: WorstBot):
        self.bot = bot

    async def cog_load(self) -> None:
        await self.bot.execute("CREATE TABLE IF NOT EXISTS selfroles(guild BIGINT NOT NULL, role BIGINT PRIMARY KEY)")

    async def cog_unload(self) -> None:
        ...

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.logger.info("SelfAssignableRoles Cog online")

    @app_commands.command(name = "role")
    async def ToggleRole(self, interaction: Interaction, role: Transform[discord.Role, RoleTransformer]):
        if not role:
            return
        if role in interaction.user.roles:
            await RoleManipulation.role_remove(interaction.user, role, "WorstBot Giveme Role")
            await interaction.response.send_message(f"You have removed the {role.name} role", ephemeral = True)
        else:
            await RoleManipulation.role_add(interaction.user, role, "WorstBot Giveme Role")
            await interaction.response.send_message(f"You have added the {role.name} role", ephemeral = True)

    @app_commands.command(name = "list")
    async def ListRole(self, interaction: Interaction):
        roles = await self.bot.fetch("SELECT role FROM selfroles WHERE guild = $1", interaction.guild_id)
        if not roles:
            return await interaction.response.send_message("no roles", ephemeral = True)
        for index, value in enumerate(roles):
            roles[index] = interaction.guild.get_role(value["role"])
        embed_list = EmbedGen.SimpleEmbedList(
            title = "giveme roles",
            descriptions = "\n\n".join(f"`{i + 1}: {role.name}`" for i, role in enumerate(roles)))
        await interaction.response.send_message(embeds = embed_list, ephemeral = True)


async def setup(bot):
    await bot.add_cog(SelfAssignableRoles(bot))
