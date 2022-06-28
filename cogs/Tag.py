import discord
from discord import app_commands, Interaction
from discord.ext import commands


class Tag(commands.GroupCog, name = "tag"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.execute("CREATE TABLE IF NOT EXISTS tags(guild BIGINT NOT NULL, name VARCHAR(256) NOT NULL, value VARCHAR(1024) NOT NULL, PRIMARY KEY(guild, name))")
        print("Tag cog online")

    @app_commands.command(name = "create", description = "create a tag to recall later by name")
    async def Create(self, interaction: Interaction, tag: str):  # todo: Create / Edit modal
        ...

    @app_commands.command(name = "edit", description = "edit a pre-existing tag by name")
    async def Edit(self, interaction: Interaction, tag: str):  # todo: Create / Edit modal
        ...

    @app_commands.command(name = "rename", description = "Rename a tag")
    async def Rename(self, interaction: Interaction, OldName: str, NewName: str):
        ...

    @app_commands.command(name = "delete", description = "Delete a tag by name")
    async def Delete(self, interaction: Interaction, tag: str):
        ...

    @app_commands.command(name = "delete-all")
    async def DeleteAll(self, interaction: Interaction):
        ...

    @app_commands.command(name = "view", description = "View a tag by name")
    async def View(self, interaction: Interaction, tag: str):
        ...

    @app_commands.command(name = "random", description = "View a tag random tag")
    @app_commands.describe(tag = "randomly select from tags containing name")
    async def Random(self, interaction: Interaction, tag: str = "%"):
        ...

    @app_commands.command(name = "search", description = "Search tags by name")
    async def Search(self, interaction: Interaction, tag: str):
        ...

    @app_commands.command(name = "list", description = "View all tags by a set user")
    @app_commands.describe(tag = "leave Blank to search your own tags")
    async def List(self, interaction: Interaction, tag: str = None):
        ...

    @app_commands.command(name = "list-all", description = "View all tags on the server")
    async def ListAll(self, interaction: Interaction):
        ...

    @app_commands.command(name = "transfer", description = "Transfer ownership of tag to someone else")
    async def Transfer(self, interaction: Interaction, tag: str, user: discord.Member):
        ...

    @app_commands.command(name = "claim", description = "Claim ownership of orphaned tags")
    async def Claim(self, interaction: Interaction, tag: str):
        ...

async def setup(bot):
    await bot.add_cog(Tag(bot))
