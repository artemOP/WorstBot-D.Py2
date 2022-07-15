from abc import ABC
import discord
from discord import app_commands, Interaction
from discord.ext import commands
from typing import Optional

class hexTransformer(app_commands.Transformer, ABC):
    @classmethod
    async def transform(cls, interaction: Interaction, value: str) -> int:
        return int(value, 16)

class CustomRoles(commands.GroupCog, name = "role"):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot
        self.ContextMenu = app_commands.ContextMenu(
            name = "Colour Check",
            callback = self.colourCheck
        )
        self.bot.tree.add_command(self.ContextMenu)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.execute("CREATE TABLE IF NOT EXISTS customroles(guild BIGINT, member BIGINT, role BIGINT UNIQUE, colour INT)")
        print("CustomRoles cog online")

    async def FetchRole(self, *, guild: discord.Guild, member: discord.Member) -> Optional[discord.Role]:

        if (roleid := await self.bot.fetchval("SELECT role FROM customroles WHERE guild = $1 AND member = $2", guild.id, member.id)) is not None:
            role = guild.get_role(roleid)
        else:
            role = discord.utils.get(guild.roles, name = str(member))
        return role if not None else None

    async def CreateRole(self, member: discord.Member, colour: int) -> None:
        role = await member.guild.create_role(name = str(member), colour = discord.Colour(colour), hoist = False)
        position = member.top_role.position if member.top_role.position > 0 else 1
        await role.edit(position = position)
        await member.add_roles(role)
        await self.bot.execute("INSERT INTO customroles(guild, member, role, colour) VALUES ($1, $2, $3, $4) ON CONFLICT (role) DO UPDATE SET role = EXCLUDED.role", member.guild.id, member.id, role.id, colour)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if await self.bot.fetchval("SELECT roles FROM events WHERE guild = $1", member.guild.id) is False:
            return
        if (colour := await self.bot.fetchval("SELECT colour FROM customroles WHERE guild = $1 AND member = $2", member.guild.id, member.id)) is None:
            colour = int("0xff00ff", 16)
        await self.CreateRole(member, colour)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        role = await self.FetchRole(guild = member.guild, member = member)
        if role:
            await role.delete()

    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        if before.bot or str(before) == str(after):
            return
        role_id = await self.bot.fetchval("SELECT role FROM customroles WHERE guild = $1 AND member = $2", before.guild.id, before.id)
        for guild in self.bot.guilds:
            if (role := guild.get_role(role_id)) is not None:
                await role.edit(name = str(after))

    @app_commands.command(name = "colour", description = "edits the colour of your custom role")
    async def EditRole(self, interaction: Interaction, colour: app_commands.Transform[int, hexTransformer]):
        role = await self.FetchRole(guild = interaction.guild, member = interaction.user)
        if not role:
            await self.CreateRole(interaction.user, colour)
        else:
            await role.edit(colour = colour)
        await interaction.response.send_message(content = f'your role colour has now been set to {hex(colour)}', ephemeral = True)

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
            embed = discord.Embed(colour = role.colour, description = f"{member.name} Uses the role colour {role.colour}")
            await interaction.followup.send(embed = embed, ephemeral = True)


async def setup(bot):
    await bot.add_cog(CustomRoles(bot))
