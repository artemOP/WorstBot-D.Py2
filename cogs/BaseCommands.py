import discord
from discord import app_commands
from discord.ext import commands

class BaseCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("BaseCommands cog online")

    @app_commands.command(name="ping")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Pong!{round(self.bot.latency * 1000)}ms", ephemeral = True)

    @app_commands.command(name="say")
    @app_commands.default_permissions(manage_messages = True)
    async def say(self, interaction: discord.Interaction, *, arg:str="what?"):
        await interaction.response.send_message(ephemeral=True,content="\u200b")
        await interaction.channel.send(content=arg)

    @app_commands.command(name="purge")
    @app_commands.default_permissions(manage_messages=True)
    async def purge(self, interaction: discord.Interaction, amount:int=1):
        await interaction.channel.purge(limit=amount)
        await interaction.response.send_message(ephemeral=True,content=f"attempted to delete {amount} messages")

    @app_commands.command(name="kick")
    @app_commands.default_permissions(kick_members=True)
    async def kick(self,interaction:discord.Interaction,member:discord.Member,*,reason:str=None):
        await member.kick(reason=reason)
        await interaction.response.send_message(f"kicked {member.name} for: `{reason}`")

    @app_commands.command(name="ban")
    @app_commands.default_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, *, reason: str = None):
        await member.ban(reason=reason)
        await interaction.response.send_message(f"banned {member.name} for: `{reason}`")

    @app_commands.command(name="unban")
    @app_commands.default_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, member:str):
        try:
            await interaction.guild.unban(discord.Object(int(member)))
            await interaction.response.send_message(f"Unban succeeded")
        except discord.NotFound:
            await interaction.response.send_message(f"User not found",ephemeral=True)

    ############################
    # error clearing
    ############################

    @purge.error
    async def purge_error(self,interaction:discord.Interaction, error:app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await MissingPermissions(interaction, "purge")
        else:
            raise

    @kick.error
    async def purge_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await MissingPermissions(interaction, "kick")
        else:
            raise

    @ban.error
    async def purge_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await MissingPermissions(interaction, "ban/unban")
        else:
            raise

    @unban.error
    async def purge_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await MissingPermissions(interaction, "ban/unban")
        else:
            raise

async def MissingPermissions(interaction:discord.Interaction, permission:str):
    await interaction.response.send_message(f"You are missing the {permission} permission")

async def setup(bot):
    await bot.add_cog(BaseCommands(bot))
