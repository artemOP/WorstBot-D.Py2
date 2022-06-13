from os import listdir

import discord
from discord import app_commands
from discord.ext import commands


@app_commands.default_permissions()
class PersonalCommands(commands.GroupCog, name = "admin"):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("PersonalCommands cog online")

    @staticmethod
    async def owner_only(interaction: discord.Interaction):
        return await interaction.client.is_owner(interaction.user)

    @app_commands.command(name = "load")
    @app_commands.check(owner_only)
    async def CogLoad(self, interaction: discord.Interaction, cog: str):
        await self.bot.load_extension(f"cogs.{cog}")
        await interaction.response.send_message(f"{cog} has been loaded", ephemeral = True)

    @app_commands.command(name = "unload")
    @app_commands.check(owner_only)
    async def CogUnload(self, interaction: discord.Interaction, cog: str):
        await self.bot.unload_extension(f"cogs.{cog}")
        await interaction.response.send_message(f"{cog} has been unloaded", ephemeral = True)

    @app_commands.command(name = "reload")
    async def CogReload(self, interaction: discord.Interaction, cog: str):
        try:
            await self.bot.reload_extension(f"cogs.{cog}")
            await interaction.response.send_message(f"{cog} has been reloaded", ephemeral = True)
        except:
            await interaction.response.send_message(f"{cog} is not a valid input", ephemeral = True)

    @CogLoad.autocomplete("cog")
    @CogUnload.autocomplete("cog")
    @CogReload.autocomplete("cog")
    async def CogAutocomplete(self, interaction: discord.Interaction, current):
        return [app_commands.Choice(name = cog[:-3], value = cog[:-3]) for cog in listdir("cogs") if cog.endswith(".py") and not cog.startswith("-") and current.lower() in cog.lower()]

    @app_commands.command(name = "nickname", description = "Change WorstBot's nickname")
    @app_commands.check(owner_only)
    @app_commands.default_permissions(administrator = True)
    async def nickname(self, interaction: discord.Interaction, nickname: str = ""):
        await interaction.guild.me.edit(nick = nickname)
        await interaction.response.send_message(f"nickname set to {nickname}", ephemeral = True)


async def setup(bot):
    await bot.add_cog(PersonalCommands(bot))
