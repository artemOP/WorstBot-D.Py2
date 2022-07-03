from os import listdir

import discord
from discord import app_commands, Interaction
from discord.ext import commands


@app_commands.default_permissions()
class Admin(commands.GroupCog, name = "admin"):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Admin cog online")

    @staticmethod
    async def owner_only(interaction: Interaction):
        return await interaction.client.is_owner(interaction.user)

    @app_commands.command(name = "load")
    @app_commands.check(owner_only)
    async def CogLoad(self, interaction: Interaction, cog: str):
        await self.bot.load_extension(f"cogs.{cog}")
        await interaction.response.send_message(f"{cog} has been loaded", ephemeral = True)

    @app_commands.command(name = "unload")
    @app_commands.check(owner_only)
    async def CogUnload(self, interaction: Interaction, cog: str):
        await self.bot.unload_extension(f"cogs.{cog}")
        await interaction.response.send_message(f"{cog} has been unloaded", ephemeral = True)

    @app_commands.command(name = "reload")
    async def CogReload(self, interaction: Interaction, cog: str):
        try:
            await self.bot.reload_extension(f"cogs.{cog}")
            await interaction.response.send_message(f"{cog} has been reloaded", ephemeral = True)
        except:
            await interaction.response.send_message(f"{cog} is not a valid input", ephemeral = True)

    @CogLoad.autocomplete("cog")
    @CogUnload.autocomplete("cog")
    @CogReload.autocomplete("cog")
    async def CogAutocomplete(self, interaction: Interaction, current):
        return [app_commands.Choice(name = cog[:-3], value = cog[:-3]) for cog in listdir("cogs") if
                cog.endswith(".py") and not cog.startswith("-") and current.lower() in cog.lower()]

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

async def setup(bot):
    await bot.add_cog(Admin(bot))
