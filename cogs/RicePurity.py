from json import load
from typing import Any

import discord
from discord import Interaction, app_commands
from discord.ext import commands
from discord.ui import Button, Item, button

from modules.EmbedGen import EmbedField, EmbedFieldList
from modules.Paginators import ButtonPaginatedEmbeds


def generator():
    with open(f"JSON/RicePurity.json", "r") as f:  # reads file
        questions = load(f)
    for i in range(0, len(questions)):
        yield str(i + 1), questions[i]


class PurityButtons(discord.ui.View):  # Makes The quiz buttons run and gives output
    def __init__(self, timeout, bot: commands.Bot):
        super().__init__(timeout = timeout)
        self.response = None
        self.score = 101
        self.counter = 0
        self.generator = generator()
        self.bot = bot

    async def on_timeout(self) -> None:
        await self.response.edit(view = None)

    async def on_error(self, interaction: Interaction, error: Exception, item: Item[Any]) -> None:
        await interaction.response.edit_message(content = error)

    async def on_complete(self, interaction: Interaction):
        await self.on_timeout()
        await interaction.response.edit_message(content = f"Your score was:{self.score}")
        await self.bot.execute("INSERT INTO ricepurity(id, score) VALUES($1, $2) ON CONFLICT (id) DO UPDATE SET score = excluded.score", interaction.user.id, self.score)

    @button(emoji = "✅", style = discord.ButtonStyle.grey)
    async def tick(self, interaction: Interaction, button: Button):
        self.score -= 1
        self.counter += 1
        if self.counter == 100:
            await self.on_complete(interaction)
        else:
            await interaction.response.edit_message(view = self, content = ": ".join(next(self.generator)))

    @button(emoji = "❌", style = discord.ButtonStyle.grey)
    async def cross(self, interaction: Interaction, button: Button):
        match self.counter:
            case 0:
                await interaction.response.edit_message(content = "Test Cancelled")
                await self.on_timeout()
            case 100:
                await self.on_complete(interaction)
            case _:
                self.counter += 1
                await interaction.response.edit_message(view = self, content = ": ".join(next(self.generator)))

class RicePurity(commands.GroupCog, name = "ricepurity"):  # Main cog class
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    async def cog_load(self) -> None:
        await self.bot.execute("CREATE TABLE IF NOT EXISTS ricepurity(id BIGINT PRIMARY KEY, score INT)")

    async def cog_unload(self) -> None:
        ...

    @commands.Cog.listener()
    async def on_ready(self):
        print("RicePurity cog online")

    @app_commands.command(name = "test")
    async def test(self, interaction: Interaction):
        view = PurityButtons(timeout = 30, bot = self.bot)
        await interaction.response.send_message('Are you ready to begin your rice purity test?', view = view, ephemeral = True)
        view.response = await interaction.original_response()

    @app_commands.command(name = "leaderboard")
    async def leaderboard(self, interaction: Interaction):
        users = {}
        for member in interaction.guild.members:
            if (score := await self.bot.fetchval("SELECT score FROM ricepurity WHERE id=$1", member.id)) is not None:
                users[member.id] = score
        embed_list = EmbedFieldList(
            title = "Rice Purity Scores",
            fields = [
                EmbedField(
                    name = str(await self.bot.maybe_fetch_user(userid)),
                    value = str(user_score))
                for userid, user_score in sorted(users.items(), key = lambda item: item[1])
            ],
            max_fields = 9,
            colour = discord.Colour.dark_purple()
        )
        view = ButtonPaginatedEmbeds(timeout = 30, embed_list = embed_list)
        await interaction.response.send_message(view = view, embed = view.embedlist[0], ephemeral = True)
        view.response = await interaction.original_response()


async def setup(bot):
    await bot.add_cog(RicePurity(bot))
