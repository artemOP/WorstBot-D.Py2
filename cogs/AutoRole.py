import discord
from discord import app_commands, Interaction
from discord.ext import commands
from WorstBot import WorstBot
from modules import EmbedGen, Paginators, RoleManipulation

@app_commands.default_permissions(manage_roles = True)
class AutoRole(commands.GroupCog, name = "autorole"):
    def __init__(self, bot: WorstBot):
        super().__init__()
        self.bot = bot
        self.logger = self.bot.logger.getChild(self.qualified_name)

    async def cog_load(self) -> None:
        await self.bot.execute("CREATE TABLE IF NOT EXISTS autorole(guild BIGINT, role BIGINT UNIQUE )")
        self.logger.info(f"{self.qualified_name} cog loaded")

    async def cog_unload(self) -> None:
        self.logger.info(f"{self.qualified_name} cog unloaded")

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
        embed_list = EmbedGen.EmbedFieldList(
            title = "Automatically applied roles",
            fields = [
                EmbedGen.EmbedField(
                    name = "Role",
                    value = "Broken Role" if not (role := interaction.guild.get_role(role_id["role"])) else role.mention)
                for role_id in roles
            ],
            max_fields = 9
        )
        view = Paginators.ButtonPaginatedEmbeds(timeout = 60, embed_list = embed_list)
        await interaction.response.send_message(view = view, embed = view.embedlist[0], ephemeral = True)
        view.response = await interaction.original_response()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if await self.bot.events(member.guild.id, self.bot._events.autorole) is False:
            return
        roles = await self.bot.fetch("SELECT role FROM autorole WHERE guild=$1", member.guild.id)
        for row in roles:
            role = member.guild.get_role(row["role"])
            if not role:
                await self.bot.execute("DELETE FROM autorole WHERE role=$1", row["role"])
                continue
            await RoleManipulation.role_add(member, role, "WorstBot AutoRole")

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        await self.bot.execute("DELETE FROM autorole WHERE role = $1", role.id)


async def setup(bot):
    await bot.add_cog(AutoRole(bot))
