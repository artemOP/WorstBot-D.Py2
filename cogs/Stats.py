import discord
from discord import app_commands, Interaction
from discord.ext import commands
from os import path, listdir
from dataclasses import dataclass, field, MISSING


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
        embed = discord.Embed(title = "stats", colour = discord.Colour.random())
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
            embed.description = f"""
                source code: {self.source} ({self.to_percent(self.source)}%)\n
                comments: {self.comment} ({self.to_percent(self.comment)}%)\n
                blank: {self.blank} ({self.to_percent(self.blank)}%)\n
                total: {self.total}\n\u200b
                """
            embed.add_field(
                name = [k for k, v in cogs.items() if v == cog][0][:-3],
                value = f"""
                source code: {cog.source} ({cog.to_percent(cog.source)}%)\n
                comments: {cog.comment} ({cog.to_percent(cog.comment)}%)\n
                blank: {cog.blank} ({cog.to_percent(cog.blank)}%)\n
                total: {cog.total}\n\u200b
                """
            )
        await interaction.response.send_message(embed = embed, ephemeral = True)


# todo:more stats(server count, command count etc etc)


async def setup(bot):
    await bot.add_cog(Stats(bot))
