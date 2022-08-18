import discord
from discord import app_commands, Interaction
from discord.ext import commands

from modules.EmbedGen import EmbedField, EmbedFieldList
from modules.Paginators import ButtonPaginatedEmbeds

@app_commands.default_permissions(manage_roles = True)
class AutoRole(commands.GroupCog, name = "autorole"):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("AutoRole cog online")
        await self.bot.execute("CREATE TABLE IF NOT EXISTS autorole(guild BIGINT, role BIGINT UNIQUE )")

    @app_commands.command(name = "setup", description = "add or remove role from autorole")
    async def AutoRole(self, interaction: Interaction, role: discord.Role):
        if not await self.bot.fetchval("SELECT EXISTS(SELECT 1 FROM autorole WHERE guild = $1 AND role = $2)", interaction.guild_id, role.id):
            await self.bot.execute("INSERT INTO autorole(guild, role) VALUES($1, $2) ON CONFLICT (role) DO NOTHING", interaction.guild.id, role.id)
            await interaction.response.send_message(f"{role.name} successfully added to the AutoRole", ephemeral = True)
        else:
            await self.bot.execute("DELETE FROM autorole WHERE guild = $1 AND role = $2", interaction.guild.id, role.id)
            await interaction.response.send_message(content = f"{role.name} successfully removed to the AutoRole", ephemeral = True)

    @app_commands.command(name = "list")
    async def AutoRoleList(self, interaction: Interaction):
        roles = await self.bot.fetch("SELECT role FROM autorole WHERE guild=$1", interaction.guild.id)
        for role in roles:
            roles[roles.index(role)] = interaction.guild.get_role(role["role"])
        embed_list = EmbedFieldList(
            title = "Automatically applied roles",
            fields = [EmbedField(name = "Role", value = role.mention) for role in roles],
            max_fields = 9
        )
        view = ButtonPaginatedEmbeds(timeout = 60, embed_list = embed_list)
        await interaction.response.send_message(view = view, embed = view.embedlist[0], ephemeral = True)
        view.response = await interaction.original_response()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if await self.bot.fetchval("SELECT autorole FROM events WHERE guild = $1", member.guild.id) is False:
            return
        roles = await self.bot.fetch("SELECT role FROM autorole WHERE guild=$1", member.guild.id)
        for role in roles:
            role = member.guild.get_role(role["role"])
            try:
                await member.add_roles(role)
            except Exception:
                pass


async def setup(bot):
    await bot.add_cog(AutoRole(bot))
