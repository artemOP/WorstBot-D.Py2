from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands

class CustomRoles(commands.GroupCog,name="role"):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.execute("CREATE TABLE IF NOT EXISTS CustomRoles(guild BIGINT, member BIGINT, role BIGINT UNIQUE )")
        print("BaseEvents cog online")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        role = await member.guild.create_role(name=str(member), colour=discord.Color(value=int("0xff00ff", 16)),hoist=False)
        await role.edit(position=member.top_role.position - 1)
        await member.add_roles(role)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        try:
            role = discord.utils.get(member.guild.roles, name=str(member))
            await role.delete()
        except:
            return

    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        for guild in self.bot.guilds:
            try:
                if before.bot is False:
                    role = discord.utils.get(guild.roles, name=str(before))
                    if role is not None:
                        await role.edit(name=str(after))
            except:
                raise

    async def CreateRole(self,interaction:discord.Interaction,colour:discord.Colour):
        role = await interaction.guild.create_role(name=str(interaction.user.name), colour=colour, hoist=False)
        await role.edit(position=interaction.user.top_role.position - 1)
        await interaction.user.add_roles(role)
        await self.bot.execute("INSERT INTO CustomRoles(guild, member, role) VALUES($1,$2,$3) ON CONFLICT (role) DO UPDATE SET role = EXCLUDED.role", interaction.guild.id, interaction.user.id, role.id)

    @app_commands.command(name="colour")
    async def EditRole(self, interaction:discord.Interaction, colour: str):
        colour = discord.Colour(value=int(colour, 16))
        role = await self.bot.fetchval("SELECT role FROM CustomRoles WHERE guild=$1 AND member=$2", interaction.guild.id,interaction.user.id)
        if role:
            try:
                role = interaction.guild.get_role(role)
                await role.edit(colour=colour)
            except:
                await self.CreateRole(interaction, colour)
        else:
            await self.CreateRole(interaction, colour)
        await interaction.response.send_message(content=f'your colour has now been set to {colour}',ephemeral=True)

    @app_commands.command(name="check")
    async def colourCheck(self, interaction:discord.Interaction, arg: Optional[discord.User] = None):
        if arg:
            user = arg.id
        else:
            user = interaction.user.id
        role = await self.bot.fetchval("SELECT role FROM CustomRoles WHERE guild=$1 AND member=$2", interaction.guild.id, user)
        role = interaction.guild.get_role(role)
        user = interaction.guild.get_member(user)
        if role is not None:
            embed = discord.Embed(colour=role.colour)
            embed.add_field(name=f"{user.name}#{user.discriminator}", value=f"Uses the role colour: {role.colour}", inline=False)
            await interaction.response.send_message(embed=embed,ephemeral=True)
        else:
            await interaction.response.send_message(content=f"{user.name}#{user.discriminator} has no custom role",ephemeral=True)

    @EditRole.error
    async def editrole_error(self,interaction:discord.Interaction, error:app_commands.AppCommandError):
        if isinstance(error, commands.MissingRequiredArgument):
            await interaction.response.send_message(f'{interaction.user.mention} please include a hex colour such as "ff00ff"')
        elif isinstance(error, commands.CommandInvokeError):
            await interaction.response.send_message(f'{interaction.user.mention} please include a hex colour such as "ff00ff"')
        elif isinstance(error, commands.BotMissingPermissions):
            await interaction.response.send_message(f'{interaction.user.mention} the bot is missing permisions, please move higher up the hierarchy')
        elif isinstance(error, commands.MissingPermissions):
            await interaction.response.send_message(f'{interaction.user.mention} you are missing the required permissions to use this command')
        else:
            raise error#TODO:move into global handler

async def setup(bot):
    await bot.add_cog(CustomRoles(bot))
