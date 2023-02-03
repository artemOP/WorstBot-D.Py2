import discord
from discord import app_commands, Interaction
from discord.ext import commands, tasks
from discord.app_commands import Choice, Transform, Transformer
from WorstBot import WorstBot
from modules import EmbedGen, Converters, RoleManipulation
from typing import Optional
from rapidfuzz import process

class RoleTransformer(Transformer):

    @staticmethod
    async def return_roles(interaction: Interaction) -> Optional[list[discord.Role]]:
        return interaction.client.giveme_roles.get(interaction.guild)

    async def transform(self, interaction: Interaction, value: str) -> Optional[discord.Role]:
        roles = await self.return_roles(interaction)
        if roles:
            return next((role for role in roles if role.id == Converters.to_int(value)), None)
        return None

    async def autocomplete(self, interaction: Interaction, current: Optional[str]):
        roles = await self.return_roles(interaction)
        if not roles:
            return []
        if not current:
            return [Choice(name = role.name, value = str(role.id)) for role in roles][:25]

        fuzzy_roles = process.extract(current, [role.name for role in roles], limit = 25)
        fuzzy_roles = [role_name for role_name, value, _ in fuzzy_roles if value > 40]
        return [Choice(name = role.name, value = str(role.id)) for role in roles if role.name in fuzzy_roles]


class SelfAssignableRoles(commands.GroupCog, name = "giveme", description = "Toggle a self assignable role"):
    def __init__(self, bot: WorstBot):
        self.bot = bot

    async def cog_load(self) -> None:
        await self.bot.execute("CREATE TABLE IF NOT EXISTS selfroles(guild BIGINT NOT NULL, role BIGINT PRIMARY KEY)")
        self.bot.giveme_roles: dict[discord.Guild, list[discord.Role]] = {}
        self.fetch_giveme_roles.start()

    async def cog_unload(self) -> None:
        del self.bot.giveme_roles

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.logger.info("SelfAssignableRoles Cog online")

    @tasks.loop(count = 1)
    async def fetch_giveme_roles(self):
        role_ids = await self.bot.fetch("Select guild, array_agg(role) as roles FROM selfroles GROUP BY guild")
        for row in role_ids:
            guild = self.bot.get_guild(row["guild"])
            self.bot.giveme_roles[guild] = [guild.get_role(role_id) for role_id in row["roles"]]

    @fetch_giveme_roles.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        self.bot.giveme_roles[guild] = []

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        del self.bot.giveme_roles[guild]

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
            if not roles[index]:
                await self.bot.execute("DELETE FROM selfroles WHERE role=$1", value["role"])
        embed_list = EmbedGen.SimpleEmbedList(
            title = "giveme roles",
            descriptions = "\n\n".join(f"`{i + 1}: {'Broken role' if not role else role.name}`" for i, role in enumerate(roles)))
        await interaction.response.send_message(embeds = embed_list, ephemeral = True)


async def setup(bot):
    await bot.add_cog(SelfAssignableRoles(bot))
