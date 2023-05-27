from os import listdir
import discord
from discord import app_commands, Interaction
from discord.app_commands import Choice
from discord.ext import commands
from WorstBot import WorstBot

@app_commands.default_permissions()
class Admin(commands.GroupCog, name = "admin"):
    def __init__(self, bot: WorstBot):
        super().__init__()
        self.bot = bot
        self.logger = self.bot.logger.getChild(self.qualified_name)

    async def cog_load(self) -> None:
        self.logger.info(f"{self.qualified_name} cog loaded")

    async def cog_unload(self) -> None:
        self.logger.info(f"{self.qualified_name} cog unloaded")

    @staticmethod
    def Choices() -> list[Choice[str]]:
        return [
            Choice(name = cog[:-3], value = cog[:-3]) for cog in listdir("cogs") if
            cog.endswith(".py") and not cog.startswith("-")
        ]

    # @app_commands.command(name = "load")
    # @app_commands.choices(cog = Choices())
    # async def CogLoad(self, interaction: Interaction, cog: Choice[str]):
    #     await self.bot.load_extension(f"cogs.{cog.value}")
    #     await interaction.response.send_message(f"{cog.value} has been loaded", ephemeral = True)
    #
    # @app_commands.command(name = "unload")
    # @app_commands.choices(cog = Choices())
    # async def CogUnload(self, interaction: Interaction, cog: Choice[str]):
    #     await self.bot.unload_extension(f"cogs.{cog.value}")
    #     await interaction.response.send_message(f"{cog.value} has been unloaded", ephemeral = True)
    #
    # @app_commands.command(name = "reload")
    # @app_commands.choices(cog = Choices())
    # async def CogReload(self, interaction: Interaction, cog: Choice[str]):
    #     try:
    #         await self.bot.reload_extension(f"cogs.{cog.value}")
    #         await interaction.response.send_message(f"{cog.value} has been reloaded", ephemeral = True)
    #     except:
    #         await interaction.response.send_message(f"{cog.value} is not a valid input", ephemeral = True)

    @app_commands.command(name = "nickname")
    async def nickname(self, interaction: Interaction, nickname: str = ""):
        """Change WorstBot's nickname

        :param interaction:
        :param nickname: WorstBot's new name
        :return:
        """
        await interaction.guild.me.edit(nick = nickname)
        await interaction.response.send_message(f"nickname set to {nickname}", ephemeral = True)

    @app_commands.command(name = "profile")
    async def ProfileRemove(self, interaction: Interaction, user: discord.User, reason: str = None):
        """Remove problematic profiles

        :param interaction:
        :param user: The user profile to remove
        :param reason: The message sent to the user
        :return:
        """
        await self.bot.execute("DELETE FROM profile WHERE member = $1", user.id)
        await interaction.response.send_message(f"{user.name}'s profile has been removed")
        try:
            await user.send(f"Your profile has been deleted by an administrator for reason:\n\n {reason}")
        except discord.Forbidden:
            pass

    @app_commands.command(name = "role", description = "add or remove self assignable roles")
    async def ToggleRole(self, interaction: Interaction, role: discord.Role):
        if not await self.bot.fetchval("SELECT EXISTS(SELECT 1 FROM selfroles WHERE guild = $1 AND role = $2)", interaction.guild_id, role.id):
            await self.bot.execute("INSERT INTO selfroles(guild, role) VALUES ($1, $2) ON CONFLICT DO NOTHING", interaction.guild_id, role.id)
            await interaction.response.send_message(f"{role.name} added as a self assignable role", ephemeral = True)
            try:
                self.bot.giveme_roles[interaction.guild].append(role)
            except:
                pass
        else:
            await self.bot.execute("DELETE FROM selfroles WHERE role = $1", role.id)
            await interaction.response.send_message(f"{role.name} removed as a self assignable role", ephemeral = True)
            try:
                self.bot.giveme_roles[interaction.guild].remove(role)
            except:
                pass

    @app_commands.command(name="tags", description = "delete all tags in the guild")
    async def DeleteAll(self, interaction: Interaction):
        await self.bot.execute("DELETE FROM tags WHERE guild = $1", interaction.guild_id)
        await interaction.response.send_message(f"Deleted all tags", ephemeral = True)

    @app_commands.command(name = "birthdays", description = "Set or remove Birthday alerts channel")
    async def BirthdayChannel(self, interaction: Interaction, channel: discord.TextChannel = None):
        if not channel:
            await self.bot.execute("DELETE FROM birthdaychannel WHERE guild = $1", interaction.guild_id)
            return await interaction.response.send_message("Birthday channel has been removed", ephemeral = True)
        await self.bot.execute("INSERT INTO birthdaychannel(guild, channel) VALUES($1, $2) ON CONFLICT(guild) DO UPDATE SET channel = $2", interaction.guild_id, channel.id)
        await interaction.response.send_message(f"Birthday channel is now {channel.mention}", ephemeral = True)

async def setup(bot):
    await bot.add_cog(Admin(bot))
