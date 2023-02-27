import discord
from discord import app_commands, Interaction
from discord.ext import commands, tasks
from discord.app_commands import Choice, Transform, Transformer
from discord.utils import MISSING
from WorstBot import WorstBot
from dataclasses import dataclass
from modules import EmbedGen, Converters, Graphs, Paginators
from datetime import date, datetime
from os import walk, getcwd, listdir

@dataclass()
class File:
    total_lines: int
    source_lines: int = 0
    comment_lines: int = 0
    blank_lines: int = 0


class DateTransformer(Transformer):

    async def autocomplete(self, interaction: Interaction, value: int | float | str, /) -> list[Choice[int | float | str]]:
        now_str = datetime.now().strftime("%Y/%m/%d")
        return [Choice(name = now_str, value = now_str)]

    @classmethod
    async def transform(cls, interaction: Interaction, value: str) -> datetime:
        return Converters.to_datetime(value, "%Y/%m/%d")


class Stats(commands.GroupCog, name = "stats"):

    def __init__(self, bot: WorstBot):
        self.bot = bot
        self.line_count: dict[str, File] = {}

    async def cog_load(self) -> None:
        await self.bot.execute("CREATE TABLE IF NOT EXISTS usage(command TEXT, guild BIGINT, execution_time timestamptz)")
        self.file_finder.start()

    async def cog_unload(self) -> None:
        self.file_finder.stop()

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.logger.info("Stats cog online")

    @tasks.loop(count = 1)
    async def file_finder(self):
        for directory in next(walk(getcwd()))[1]:
            if directory.startswith((".", "-")):
                continue
            for file in listdir(directory):
                self.bot.logger.debug(f"dispatch {file}")
                self.bot.dispatch("cog_reload", root = directory, file = file)

    @file_finder.before_loop
    async def wait_until_ready(self):
        await self.bot.wait_until_ready()

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
        embed_list = EmbedGen.EmbedFieldList(
            author = {"name": author.get("login"), "url": author.get("html_url"), "icon_url": author.get("avatar_url")},
            fields = [
                EmbedGen.EmbedField(
                    name = date.fromtimestamp(week.get("w")).strftime("%d/%m/%Y"),
                    value = f"""Additions: {week.get("a")}\nDeletions: {week.get("d")}\n Commits:{week.get("c")}\n"""
                ) for week in data if not (week["a"] == 0 and week["d"] == 0 and week["c"] == 0)
            ],
            max_fields = 9
        )
        view = Paginators.ButtonPaginatedEmbeds(timeout = 30, embed_list = embed_list)
        await interaction.followup.send(view = view, embed = embed_list[0], content = f"Total commits: {contributors.get('data').get('total')}", ephemeral = True)
        view.response = await interaction.original_response()

    @app_commands.command(name = "server-usage", description = "WorstBot usage on this server")
    @app_commands.describe(before = "YYYY/MM/DD", after = "YYYY/MM/DD")
    async def GuildUsage(self, interaction: Interaction, before: Transform[str, DateTransformer] = Converters.to_datetime("2100/01/01", "%Y/%m/%d"), after: Transform[str, DateTransformer] = Converters.to_datetime("1970/01/01", "%Y/%m/%d")):
        await interaction.response.defer(ephemeral = True)

        usage = await self.bot.fetch("SELECT command, COUNT(*) AS count FROM usage WHERE guild = $1 AND execution_time BETWEEN $2::TIMESTAMP AND $3::TIMESTAMP GROUP BY command ORDER BY count DESC", interaction.guild_id, after, before)
        total = sum(row["count"] for row in usage)
        chartIO = await Graphs.graph("pie", self.bot.loop, {row["command"]: row["count"] for row in usage if (row["count"] / total) * 100 > 3})
        view = Paginators.ThemedGraphView({"Light": chartIO[0], "Dark": chartIO[1]})
        embeds = EmbedGen.SimpleEmbedList(title = "Guild command usage",
                                          descriptions = "\n".join(
                                              f"{row['command']}: {row['count']}" for row in usage),
                                          image = "attachment://image.png",
                                          footer = {"text": f"Total uses: {total}"}
                                          )
        await interaction.followup.send(view = view, embeds = embeds, file = discord.File(fp = chartIO[1], filename = "image.png"))
        view.response = await interaction.original_response()

    @app_commands.command(name = "global-usage", description = "Global WorstBot usage")
    async def GloablUsage(self, interaction: Interaction):
        await interaction.response.defer(ephemeral = True)
        usage = await self.bot.fetch("SELECT command, COUNT(*) as count, max(execution_time) as last_usage FROM usage GROUP BY command ORDER BY count DESC")
        total = sum(row["count"] for row in usage)
        chartIO = await Graphs.graph("pie", self.bot.loop, {row["command"]: row["count"] for row in usage if (row["count"] / total) * 100 > 3})
        view = Paginators.ThemedGraphView({"Light": chartIO[0], "Dark": chartIO[1]})
        embeds = EmbedGen.SimpleEmbedList(title = "Global command usage",
                                          descriptions = "\n".join(
                                              f"{row['command']}: {row['count']} (Last used: {row['last_usage'].strftime('%Y/%m/%d')})"
                                              for row in usage),
                                          image = "attachment://image.png",
                                          footer = {"text": f"Total uses: {total}"}
                                          )
        await interaction.followup.send(view = view, embeds = embeds, file = discord.File(fp = chartIO[1], filename = "image.png"))
        view.response = await interaction.original_response()

    @app_commands.command(name = "line-count", description = "Display the line count for Worstbot")
    async def line_count(self, interaction: Interaction):
        total_lines: File = File(total_lines = 0)
        fields = []
        for key, file in self.line_count.items():  # type: str, File
            fields.append(
                EmbedGen.EmbedField(
                    name = key,
                    value = await self.text_formatting(file)
                )
            )
            total_lines.source_lines += file.source_lines
            total_lines.comment_lines += file.comment_lines
            total_lines.blank_lines += file.blank_lines
            total_lines.total_lines += sum((file.source_lines, file.comment_lines, file.blank_lines))

        author = {
            "name": interaction.guild.me.display_name,
            "url": "https://github.com/artemOP/WorstBot-D.Py2",
            "icon_url": interaction.guild.me.display_avatar.url
        }
        embed_list = EmbedGen.EmbedFieldList(
            author = author,
            title = "Line Count",
            fields = fields,
            max_fields = 9
        )
        embed_list.insert(
            0,
            EmbedGen.SimpleEmbed(
                title = "Project total",
                author = author,
                text = await self.text_formatting(total_lines)
            )
        )
        view = Paginators.ButtonPaginatedEmbeds(timeout = 60, embed_list = embed_list)
        await interaction.response.send_message(view = view, embed = embed_list[0], ephemeral = True)
        view.response = await interaction.original_response()

    @commands.Cog.listener(name = "on_app_command_completion")
    async def CommandUsage(self, interaction: Interaction, command: app_commands.Command | app_commands.ContextMenu) -> None:
        if await self.bot.events(interaction.guild_id, self.bot._events.usage) is False:
            return
        await self.bot.execute("INSERT INTO usage(command, guild, execution_time) VALUES($1, $2, $3)", command.qualified_name, interaction.guild_id, interaction.created_at)

    @commands.Cog.listener()
    async def on_cog_reload(self, root: str = None, file: str = MISSING):
        self.bot.logger.debug(f"Event triggered: {root}/{file}")
        if not root:
            root, file = file.split(".", maxsplit = 1)
        if file.startswith("-") or not file.endswith(".py"):
            self.bot.logger.debug(f"Early return on {root}/{file}")
            return
        with open(f"{root}/{file}", encoding = "utf-8") as f:
            self.line_count[file] = await self.file_analysis(f.readlines())
        self.line_count = dict(sorted(self.line_count.items(), key = lambda x: x[1].total_lines, reverse = True))

    @staticmethod
    async def file_analysis(lines: list[str]) -> File:
        file = File(len(lines))
        block_size = 0
        for line in lines:
            if line == "\n":
                file.blank_lines += 1
            elif "#" in line:
                file.comment_lines += 1
            elif '"""' in line:
                if block_size != 0 or line.count('"""') % 2 == 0:
                    file.comment_lines += block_size + 1
                    block_size = 0
                else:
                    block_size += 1
            else:
                if block_size != 0:
                    block_size += 1
                else:
                    file.source_lines += 1
        return file

    @staticmethod
    async def text_formatting(file: File) -> str:
        return f"""
                source code: {file.source_lines} ({Converters.to_percent(file.source_lines, file.total_lines)}%)\n
                comments: {file.comment_lines} ({Converters.to_percent(file.comment_lines, file.total_lines)}%)\n
                blank: {file.blank_lines} ({Converters.to_percent(file.blank_lines, file.total_lines)}%)\n
                total: {file.total_lines}\n\u200b
                """


async def setup(bot):
    await bot.add_cog(Stats(bot))
