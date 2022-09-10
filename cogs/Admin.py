from os import listdir
import discord
from discord import app_commands, Interaction
from discord.app_commands import Choice
from discord.ext import commands

@app_commands.default_permissions()
class Admin(commands.GroupCog, name = "admin"):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    async def cog_load(self) -> None:
        ...

    async def cog_unload(self) -> None:
        ...

    @commands.Cog.listener()
    async def on_ready(self):
        print("Admin cog online")

    @staticmethod
    async def owner_only(interaction: Interaction):
        return await interaction.client.is_owner(interaction.user)

    @staticmethod
    def Choices() -> list[Choice[str]]:
        return [
            Choice(name = cog[:-3], value = cog[:-3]) for cog in listdir("cogs") if
            cog.endswith(".py") and not cog.startswith("-")
        ]

    @app_commands.command(name = "load")
    @app_commands.check(owner_only)
    @app_commands.choices(cog = Choices())
    async def CogLoad(self, interaction: Interaction, cog: Choice[str]):
        await self.bot.load_extension(f"cogs.{cog.value}")
        await interaction.response.send_message(f"{cog.value} has been loaded", ephemeral = True)

    @app_commands.command(name = "unload")
    @app_commands.check(owner_only)
    @app_commands.choices(cog = Choices())
    async def CogUnload(self, interaction: Interaction, cog: Choice[str]):
        await self.bot.unload_extension(f"cogs.{cog.value}")
        await interaction.response.send_message(f"{cog.value} has been unloaded", ephemeral = True)

    @app_commands.command(name = "reload")
    @app_commands.choices(cog = Choices())
    async def CogReload(self, interaction: Interaction, cog: Choice[str]):
        try:
            await self.bot.reload_extension(f"cogs.{cog.value}")
            await interaction.response.send_message(f"{cog.value} has been reloaded", ephemeral = True)
        except:
            await interaction.response.send_message(f"{cog.value} is not a valid input", ephemeral = True)

    @app_commands.command(name = "nickname", description = "Change WorstBot's nickname")
    @app_commands.check(owner_only)
    async def nickname(self, interaction: Interaction, nickname: str = ""):
        await interaction.guild.me.edit(nick = nickname)
        await interaction.response.send_message(f"nickname set to {nickname}", ephemeral = True)

    @app_commands.command(name = "profile", description = "admin command to remove problematic profiles")
    async def ProfileRemove(self, interaction: Interaction, user: discord.User, reason: str = None):
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
        else:
            await self.bot.execute("DELETE FROM selfroles WHERE role = $1", role.id)
            await interaction.response.send_message(f"{role.name} removed as a self assignable role", ephemeral = True)

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
