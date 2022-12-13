from abc import ABC
import discord
from discord import app_commands, Interaction
from discord.ext import commands
from discord.app_commands import Transform, Transformer
from os import listdir
from dataclasses import dataclass, field, MISSING
from modules import EmbedGen, Converters, Graphs
from datetime import date, datetime


@dataclass
class Cog:
    lines: list = MISSING
    source: int = 0
    comment: int = 0
    blank: int = 0
    total: int = field(init = False)

    def __post_init__(self):
        self.total = len(self.lines)


class DateTransformer(Transformer, ABC):

    @classmethod
    async def transform(cls, interaction: Interaction, value: str) -> datetime:
        return Converters.to_datetime(value, "%Y/%m/%d")

class Stats(commands.GroupCog, name = "stats"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.source = 0
        self.comment = 0
        self.blank = 0
        self.total = 0

    async def cog_load(self) -> None:
        await self.bot.execute("CREATE TABLE IF NOT EXISTS usage(command TEXT, guild BIGINT, execution_time timestamptz)")

    async def cog_unload(self) -> None:
        ...

    @commands.Cog.listener()
    async def on_ready(self):
        print("Stats cog online")

    @app_commands.command(name = "line-count", description = "display the line count stats for worstbot")
    async def LineCount(self, interaction: Interaction):
        await interaction.response.defer(ephemeral = True)
        fields: list[EmbedGen.EmbedField] = []
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
                EmbedGen.EmbedField(name = [k for k, v in cogs.items() if v == cog][0][:-3],
                                    value = f"""
                           source code: {cog.source} ({Converters.to_percent(cog.source, cog.total)}%)\n
                           comments: {cog.comment} ({Converters.to_percent(cog.comment, cog.total)}%)\n
                           blank: {cog.blank} ({Converters.to_percent(cog.blank, cog.total)}%)\n
                           total: {cog.total}\n\u200b
                           """
                                    )
            )
        embeds = EmbedGen.EmbedFieldList(title = "stats", fields = fields, max_fields = 12)
        embeds.insert(0,
                      EmbedGen.SimpleEmbed(
                          title = "Project total",
                          text = f"""
                          source code: {self.source} ({Converters.to_percent(self.source, self.total)}%)\n
                          comments: {self.comment} ({Converters.to_percent(self.comment, self.total)}%)\n
                          blank: {self.blank} ({Converters.to_percent(self.blank, self.total)}%)\n
                          total: {self.total}\n\u200b"""))
        await interaction.followup.send(embeds = embeds, ephemeral = True)

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
        embed = EmbedGen.FullEmbed(
            author = {"name": author.get("login"), "url": author.get("html_url"), "icon_url": author.get("avatar_url")},
            fields = [
                EmbedGen.EmbedField(
                    name = date.fromtimestamp(week.get("w")).strftime("%d/%m/%Y"),
                    value = f"""Additions: {week.get("a")}\nDeletions: {week.get("d")}\n Commits:{week.get("c")}\n"""
                ) for week in data
            ],
            footer = {"text": f"Total commits: {contributors.get('data').get('total')}", "icon_url": author.get("avatar_url")},
            thumbnail = author.get("avatar_url")
        )
        await interaction.followup.send(embed = embed, ephemeral = True)

    @app_commands.command(name = "server-usage", description = "WorstBot usage on this server")
    @app_commands.describe(before = "YYYY/MM/DD", after = "YYYY/MM/DD")
    async def GuildUsage(self, interaction: Interaction, before: Transform[str, DateTransformer] = Converters.to_datetime("2100/01/01", "%Y/%m/%d"), after: Transform[str, DateTransformer] = Converters.to_datetime("1970/01/01", "%Y/%m/%d")):
        await interaction.response.defer(ephemeral = True)

        usage = await self.bot.fetch("SELECT command, COUNT(*) AS count FROM usage WHERE guild = $1 AND execution_time BETWEEN $2::TIMESTAMP AND $3::TIMESTAMP GROUP BY command ORDER BY count DESC", interaction.guild_id, after, before)
        chartIO = await Graphs.graph("pie", self.bot.loop, {row["command"]: row["count"] for row in usage})
        embeds = EmbedGen.SimpleEmbedList(title = "Guild command usage",
                                          descriptions = "\n".join(
                                              f"{row['command']}: {row['count']}" for row in usage),
                                          image = "attachment://image.png")
        await interaction.followup.send(embeds = embeds, file = discord.File(fp = chartIO, filename = "image.png"))

    @app_commands.command(name = "global-usage", description = "Global WorstBot usage")
    async def GloablUsage(self, interaction: Interaction):
        await interaction.response.defer(ephemeral = True)
        usage = await self.bot.fetch("SELECT command, COUNT(*) as count, max(execution_time) as last_usage FROM usage GROUP BY command ORDER BY count DESC")
        chartIO = await Graphs.graph("pie", self.bot.loop, {row["command"]: row["count"] for row in usage})
        embeds = EmbedGen.SimpleEmbedList(title = "Global command usage",
                                          descriptions = "\n".join(
                                              f"{row['command']}: {row['count']} (Last used: {row['last_usage'].strftime('%Y/%m/%d')})"
                                              for row in usage),
                                          image = "attachment://image.png")
        await interaction.followup.send(embeds = embeds, file = discord.File(fp = chartIO, filename = "image.png"))

    @commands.Cog.listener(name = "on_app_command_completion")
    async def CommandUsage(self, interaction: Interaction, command: app_commands.Command | app_commands.ContextMenu) -> None:
        if await self.bot.events(interaction.guild_id, self.bot._events.usage) is False:
            return
        await self.bot.execute("INSERT INTO usage(command, guild, execution_time) VALUES($1, $2, $3)", command.qualified_name, interaction.guild_id, interaction.created_at)


async def setup(bot):
    await bot.add_cog(Stats(bot))
