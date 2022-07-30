import discord
from discord import app_commands, Interaction
from discord.ext import commands
from os import listdir
from dataclasses import dataclass, field, MISSING
from modules.EmbedGen import FullEmbed, EmbedField
from datetime import date

@dataclass
class Cog:
    lines: list = MISSING
    source: int = 0
    comment: int = 0
    blank: int = 0
    total: int = field(init = False)

    def __post_init__(self):
        self.total = len(self.lines)

    def to_percent(self, number: int) -> int:
        return round((number / self.total) * 100)


class Stats(commands.GroupCog, name = "stats"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.source = 0
        self.comment = 0
        self.blank = 0
        self.total = 0

    @commands.Cog.listener()
    async def on_ready(self):
        print("Stats cog online")

    def to_percent(self, number: int) -> int:
        return round((number / self.total) * 100)


    @app_commands.command(name = "lines", description = "display the line count stats for worstbot")
    async def stats(self, interaction: Interaction):
        fields: list[EmbedField] = []
        cogs = {}
        blocksize = 0
        for cog in listdir("cogs"):
            if cog.startswith("-") or not cog.endswith(".py"):
                continue
            with open(f"cogs/{cog}", "r", encoding = "utf-8") as f:
                cogs[cog] = Cog(f.readlines())
            cog = cogs[cog]
            for line in cog.lines:
                if line == "\n":
                    cog.blank += 1
                    self.blank += 1
                elif "#" in line:
                    cog.comment += 1
                    self.comment += 1
                elif '"""' in line:
                    if blocksize != 0 or line.count('"""') % 2 == 0:
                        cog.comment += blocksize + 1
                        self.comment += blocksize + 1
                        blocksize = 0
                    else:
                        blocksize += 1
                else:
                    if blocksize != 0:
                        blocksize += 1
                    else:
                        cog.source += 1
                        self.source += 1
                self.total += 1
            fields.append(
                EmbedField(name = [k for k, v in cogs.items() if v == cog][0][:-3],
                           value = f"""
                           source code: {cog.source} ({cog.to_percent(cog.source)}%)\n
                           comments: {cog.comment} ({cog.to_percent(cog.comment)}%)\n
                           blank: {cog.blank} ({cog.to_percent(cog.blank)}%)\n
                           total: {cog.total}\n\u200b
                           """
                           )
            )
        description = f"""
        source code: {self.source} ({self.to_percent(self.source)}%)\n
        comments: {self.comment} ({self.to_percent(self.comment)}%)\n
        blank: {self.blank} ({self.to_percent(self.blank)}%)\n
        total: {self.total}\n\u200b"""
        embed = FullEmbed(title = "stats", fields = fields, description = description)
        await interaction.response.send_message(embed = embed, ephemeral = True)

    @app_commands.command(name = "github", description = "Various stats about WorstBot's GitHub Repo")
    async def github(self, interaction: Interaction):
        await interaction.response.defer(ephemeral = True)
        contributors: dict | None = await self.bot.get(
            url = "https://api.github.com/repos/artemOP/WorstBot-D.Py2/stats/contributors",
            headers = {"accept": "application/vnd.github+json"})
        if not contributors:
            return await interaction.followup.send("no api response", ephemeral = True)
        elif not contributors.get("data"):
            return await interaction.followup.send("no content", ephemeral = True)
        data, author = contributors.get("data").get("weeks") or {}, contributors.get("data").get("author") or {}
        embed = FullEmbed(
            author = {"name": author.get("login"), "url": author.get("html_url"), "icon_url": author.get("avatar_url")},
            fields = [
                EmbedField(
                    name = date.fromtimestamp(week.get("w")).strftime("%d/%m/%Y"),
                    value = f"""Additions: {week.get("a")}\nDeletions: {week.get("d")}\n Commits:{week.get("c")}\n"""
                ) for week in data
            ],
            footer = {"text": f"Total commits: {contributors.get('data').get('total')}", "icon_url": author.get("avatar_url")},
            thumbnail = author.get("avatar_url")
        )
        await interaction.followup.send(embed = embed, ephemeral = True)

# todo:more stats(server count, command count etc etc)


async def setup(bot):
    await bot.add_cog(Stats(bot))
