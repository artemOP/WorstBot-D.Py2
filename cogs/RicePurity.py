from json import load
from math import ceil
import discord
from discord import app_commands, Interaction
from discord.ui import Item, Button, button
from discord.ext import commands
from typing import Any


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


class PurityLeaderboard(discord.ui.View):
    def __init__(self, timeout):
        super().__init__(timeout = timeout)
        self.response = None
        self.embedlist = None
        self.page = 0

    async def on_timeout(self) -> None:
        await self.response.edit(view = None)

    @button(label = 'First page', style = discord.ButtonStyle.red, custom_id = 'RicePurityPersistent:FirstPage')
    async def first(self, interaction: Interaction, button: Button):
        await interaction.response.edit_message(embed = self.embedlist[0])
        self.page = 0

    @button(label = 'Previous page', style = discord.ButtonStyle.red, custom_id = 'RicePurityPersistent:back')
    async def previous(self, interaction: Interaction, button: Button):
        if self.page >= 1:
            self.page -= 1
            await interaction.response.edit_message(embed = self.embedlist[self.page])
        else:
            self.page = len(self.embedlist) - 1
            await interaction.response.edit_message(embed = self.embedlist[self.page])

    @button(label = 'Stop', style = discord.ButtonStyle.grey, custom_id = 'RicePurityPersistent:exit')
    async def exit(self, interaction: Interaction, button: Button):
        await self.on_timeout()

    @button(label = 'Next Page', style = discord.ButtonStyle.green, custom_id = 'RicePurityPersistent:forward')
    async def next(self, interaction: Interaction, button: Button):
        self.page += 1
        if self.page > len(self.embedlist) - 1:
            self.page = 0
        await interaction.response.edit_message(embed = self.embedlist[self.page])

    @button(label = 'Last Page', style = discord.ButtonStyle.green, custom_id = 'RicePurityPersistent:LastPage')
    async def last(self, interaction: Interaction, button: Button):
        self.page = len(self.embedlist) - 1
        await interaction.response.edit_message(embed = self.embedlist[self.page])


class RicePurity(commands.GroupCog, name = "ricepurity"):  # Main cog class
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.execute("CREATE TABLE IF NOT EXISTS ricepurity(id BIGINT PRIMARY KEY, score INT)")
        print("RicePurity cog online")

    async def embedforming(self, users):
        embedlist = []
        totalcount = 0
        while totalcount < len(users):
            fieldcount = 0
            embed = discord.Embed(colour = discord.Colour.dark_purple(), title = "Rice Purity Scores")
            while fieldcount < 24 and totalcount < len(users):
                embed.add_field(name = self.bot.get_user(list(users.keys())[totalcount]), value = list(users.values())[
                    totalcount])
                fieldcount += 1
                totalcount += 1
            embed.set_footer(text = f"Page {ceil(totalcount / 25)} of {ceil(len(users) / 25)}")
            embedlist.append(embed)
        return embedlist

    @app_commands.command(name = "test")
    async def test(self, interaction: Interaction):
        view = PurityButtons(timeout = 60, bot = self.bot)
        await interaction.response.send_message('Are you ready to begin your rice purity test?', view = view, ephemeral = True)
        view.response = await interaction.original_message()

    @app_commands.command(name = "leaderboard")
    async def leaderboard(self, interaction: Interaction):
        view = PurityLeaderboard(timeout = 300)
        users = {}
        for member in interaction.guild.members:
            if (score := await self.bot.fetchval("SELECT score FROM ricepurity WHERE id=$1", member.id)) is not None:
                users[member.id] = score
        users = {key: value for key, value in sorted(users.items(), key = lambda item: item[1])}
        view.embedlist = await self.embedforming(users)
        await interaction.response.send_message(view = view, embed = view.embedlist[0], ephemeral = True)
        view.response = await interaction.original_message()


async def setup(bot):
    await bot.add_cog(RicePurity(bot))
