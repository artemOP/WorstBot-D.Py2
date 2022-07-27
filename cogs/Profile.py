import discord
from discord import Interaction, app_commands
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
from modules.EmbedGen import FullEmbed, EmbedField

class ProfileFill(Modal, title = "Profile field"):
    def __init__(self, *, label, name = None, value = None):
        super().__init__()
        self.label = label
        self.name = TextInput(
            label = "field name",
            placeholder = "enter the title of the field",
            default = name,
            required = True,
            max_length = 256
        )
        self.add_item(self.name)
        self.value = TextInput(
            label = "field value",
            placeholder = "enter the content of the field",
            default = value,
            required = True,
            max_length = 1024,
            style = discord.TextStyle.long
        )
        self.add_item(self.value)

    async def on_submit(self, interaction: Interaction) -> None:
        await interaction.client.execute(
            """
            INSERT INTO profile(member, name, value, index)
            VALUES($1, $2, $3, $4)
            ON CONFLICT(member, index) DO UPDATE SET name = excluded.name, value = excluded.value
            """,
            interaction.user.id, self.name.value, self.value.value, self.label)
        embed = FullEmbed(title = f"Profile Field {self.label}", fields = [EmbedField(name = self.name.value, value = self.value.value)])
        await interaction.response.send_message(embed = embed, ephemeral = True)

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        await interaction.response.send_message(str(error), ephemeral = True)


class ButtonCallback(Button):
    def __init__(self, index):
        super().__init__(
            label = index
        )

    async def callback(self, interaction: Interaction) -> None:
        row = await interaction.client.fetchrow("SELECT name, value FROM profile WHERE member = $1 AND index = $2", interaction.user.id, int(self.label))
        if row:
            name, value = row["name"], row["value"]
        else:
            name, value = None, None
        await interaction.response.send_modal(ProfileFill(label = self.label, name = name, value = value))


class ProfileView(View):
    def __init__(self, timeout):
        super().__init__(timeout = timeout)
        self.response = None
        for i in range(1, 26):
            self.add_item(ButtonCallback(i))

    async def on_timeout(self) -> None:
        await self.response.edit(view = None)

    async def on_error(self, interaction: Interaction, error: Exception, item: Button) -> None:
        await interaction.response.send_message(str(error), ephemeral = True)


class Profile(commands.GroupCog, name = "profile"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ContextMenu = app_commands.ContextMenu(
            name = "Profile",
            callback = self.ProfileContextMenu
        )
        self.bot.tree.add_command(self.ContextMenu)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.execute("CREATE TABLE IF NOT EXISTS profile(member BIGINT NOT NULL, name VARCHAR(256), value VARCHAR(1024), index SMALLINT, UNIQUE(member, index))")
        print("profile cog online")

    async def FetchProfile(self, user: int) -> discord.Embed:
        rows = await self.bot.fetch("SELECT name, value, index FROM profile WHERE member = $1", user)
        embed = FullEmbed(title = "Profile", fields = [EmbedField(index = row["index"], name = row["name"], value = row["value"]) for row in rows])
        return embed

    @app_commands.command(name = "setup", description = "Make a profile for others to see")
    async def ProfileSetup(self, interaction: Interaction):
        embed = await self.FetchProfile(interaction.user.id)
        view = ProfileView(timeout = 30)
        await interaction.response.send_message(view = view, embed = embed, ephemeral = True)
        view.response = await interaction.original_message()

    @app_commands.command(name = "view", description = "Look at a users profile")
    async def ProfileCommand(self, interaction: Interaction, user: discord.User):
        await self.ProfileContextMenu(interaction, user)

    async def ProfileContextMenu(self, interaction: Interaction, user: discord.User):
        embed = await self.FetchProfile(user.id)
        await interaction.response.send_message(embed = embed, ephemeral = True)

async def setup(bot):
    await bot.add_cog(Profile(bot))
