import discord
from discord import app_commands
from discord.ext import commands
from os import listdir


# noinspection PyUnresolvedReferences
class PersonalCommands(commands.GroupCog, name="admin"):
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
    @commands.has_permissions(administrator = True)
    async def CogReload(self, interaction: discord.Interaction, cog: str):
        await self.bot.reload_extension(f"cogs.{cog}")
        await interaction.response.send_message(f"{cog} has been reloaded", ephemeral = True)

    @app_commands.command(name = "cogs", description = "list out the subfiles within WorstBot")
    @commands.has_permissions(administrator = True)
    async def Cogs(self, interaction: discord.Interaction):
        embed = discord.Embed(colour = discord.Color.random(), title = "cogs")
        for filename in listdir("cogs"):
            if filename.endswith(".py") and not filename.startswith("-"):
                embed.add_field(name = filename[:-3], value = "\u200b", inline = True)
        await interaction.response.send_message(embed = embed, ephemeral = True)

    @app_commands.command(name = "nickname", description = "Change WorstBot's nickname")
    @app_commands.check(owner_only)
    async def nickname(self, interaction: discord.Interaction, nickname: str = ""):
        await interaction.guild.me.edit(nick = nickname)
        await interaction.response.send_message(f"nickname set to {nickname}", ephemeral = True)


async def setup(bot):
    await bot.add_cog(PersonalCommands(bot))
