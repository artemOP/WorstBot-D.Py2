import discord
from discord import Interaction, app_commands
from discord.app_commands import AppCommandError
from discord.ext import commands

class ErrorHandler(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        bot.tree.on_error = self.on_app_command_error
        bot.on_error = self.on_error

    @commands.Cog.listener()
    async def on_ready(self):
        print("Error handling cog online")

    async def on_app_command_error(self, interaction:discord.Interaction, error: AppCommandError):
        if isinstance(error, app_commands.CommandInvokeError):
            error = error.original
        match error:
            case commands.errors.ExtensionNotFound():
                await interaction.response.send_message(f"cog not found or already loaded\n\nTraceback: {error}")
            case app_commands.BotMissingPermissions():
                await interaction.response.send_message(f"WorstBot is missing the {error.missing_permissions} perms")
            case app_commands.CommandInvokeError():
                await interaction.response.send_message(f"Command errored on invoke\n\nTraceback: {error}")
            case app_commands.MissingPermissions():
                print(error)
                await interaction.response.send_message(f"You are missing the {error.missing_permissions[0]} permissions")
            case _:
                # print(error)
                raise

    async def on_error(self, interaction:discord.Interaction, error: AppCommandError):
        match error:
            case commands.ExtensionNotFound | commands.ExtensionAlreadyLoaded:
                await interaction.response.send_message(f"cog not found or already loaded\n\nTraceback: {error}")



async def setup(bot):
    await bot.add_cog(ErrorHandler(bot))
