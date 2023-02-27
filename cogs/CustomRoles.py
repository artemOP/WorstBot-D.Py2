import discord
from discord import app_commands, Interaction
from discord.app_commands import Choice
from discord.ext import commands
from WorstBot import WorstBot
from typing import Optional
from modules import EmbedGen, RoleManipulation
from asyncio import sleep

class hexTransformer(app_commands.Transformer):
    async def autocomplete(self, interaction: Interaction, value: int | float | str, /) -> list[Choice[int | float | str]]:
        return [Choice(name = "abcdef", value = "abcdef"), Choice(name = "0x012345", value = "0x012345"), Choice(name = "#1120ff", value = "#1120ff")]

    @classmethod
    async def transform(cls, interaction: Interaction, value: str) -> int:
        value = value.removeprefix("#")
        return int(value, 16)

class CustomRoles(commands.GroupCog, name = "role"):
    def __init__(self, bot: WorstBot):
        super().__init__()
        self.bot = bot
        self.ContextMenu = app_commands.ContextMenu(
            name = "Colour Check",
            callback = self.colourCheck
        )
        self.bot.tree.add_command(self.ContextMenu)

    async def cog_load(self) -> None:
        await self.bot.execute("CREATE TABLE IF NOT EXISTS customroles(guild BIGINT, member BIGINT, role BIGINT UNIQUE, colour INT, UNIQUE(guild, member))")

    async def cog_unload(self) -> None:
        ...

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.logger.info("CustomRoles cog online")

    async def FetchRole(self, *, guild: discord.Guild, member: discord.Member) -> Optional[discord.Role]:

        if (roleid := await self.bot.fetchval("SELECT role FROM customroles WHERE guild = $1 AND member = $2", guild.id, member.id)) is not None:
            role = guild.get_role(roleid)
        else:
            role = discord.utils.get(guild.roles, name = str(member))
        return role if not None else None

    async def CreateRole(self, member: discord.Member, colour: int) -> None:
        custom_role = await RoleManipulation.role_create(member.guild, name = str(member), colour = discord.Colour(colour))
        position = 1
        for role in member.roles:
            if role.position > position:
                position = role.position
        await RoleManipulation.role_edit(custom_role, position = position)
        await RoleManipulation.role_add(member, custom_role, "WorstBot Custom Coloured Roles")
        await self.bot.execute("INSERT INTO customroles(guild, member, role, colour) VALUES ($1, $2, $3, $4) ON CONFLICT (guild, member) DO UPDATE SET role = EXCLUDED.role, colour = EXCLUDED.colour", member.guild.id, member.id, custom_role.id, colour)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if await self.bot.events(member.guild.id, self.bot._events.roles) is False:
            return
        if (colour := await self.bot.fetchval("SELECT colour FROM customroles WHERE guild = $1 AND member = $2", member.guild.id, member.id)) is None:
            colour = int("0xff00ff", 16)
        await sleep(10)
        await self.CreateRole(member, colour)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        role = await self.FetchRole(guild = member.guild, member = member)
        if role:
            await RoleManipulation.role_delete(role, "WorstBot custom role no longer needed as user left the server")

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.bot or str(before) == str(after):
            return
        role_id = await self.bot.fetchval("SELECT role FROM customroles WHERE guild = $1 AND member = $2", before.guild.id, before.id)
        for guild in self.bot.guilds:
            if (role := guild.get_role(role_id)) is not None:
                await RoleManipulation.role_edit(role, name=str(after))

    @app_commands.command(name = "colour", description = "edits the colour of your custom role")
    async def EditRole(self, interaction: Interaction, colour: app_commands.Transform[int, hexTransformer]):
        await interaction.response.defer(ephemeral = True)
        role = await self.FetchRole(guild = interaction.guild, member = interaction.user)
        if not role:
            await self.CreateRole(interaction.user, colour)
        else:
            await RoleManipulation.role_edit(role, colour = colour)
        await interaction.followup.send(content = f'your role colour has now been set to {hex(colour)}', ephemeral = True)

    @app_commands.command(name = "check")
    async def colourCheckCommand(self, interaction: Interaction, arg: Optional[discord.User] = None):
        await self.colourCheck(interaction, arg)

    async def colourCheck(self, interaction: Interaction, arg: discord.User = None):
        await interaction.response.defer(ephemeral = True)
        member = arg if arg else interaction.user
        role = await self.FetchRole(guild = interaction.guild, member = member)
        if role is None:
            await interaction.followup.send("This user does not have a custom role or it may be broken")
        else:
            await interaction.followup.send(
                embed = EmbedGen.SimpleEmbed(
                    colour = role.colour,
                    text = f"{member.name} Uses the role colour {role.colour}"),
                ephemeral = True)


async def setup(bot):
    await bot.add_cog(CustomRoles(bot))
