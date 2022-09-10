import os
import pathlib

import discord
from discord.ext import commands, tasks

# put your extension names in this list
# if you don't want them to be reloaded
IGNORE_EXTENSIONS = ["-template"]


def path_from_extension(extension: str) -> pathlib.Path:
    return pathlib.Path(extension.replace('.', os.sep) + '.py')


class HotReload(commands.Cog):
    """
    Cog for reloading extensions as soon as the file is edited
    """

    def __init__(self, bot):
        self.last_modified_time = {}
        self.bot = bot

    async def cog_load(self) -> None:
        self.hot_reload_loop.start()

    async def cog_unload(self) -> None:
        self.hot_reload_loop.stop()

    @tasks.loop(seconds = 3)
    async def hot_reload_loop(self):
        for extension in list(self.bot.extensions.keys()):
            if extension in IGNORE_EXTENSIONS:
                continue
            path = path_from_extension(extension)
            time = os.path.getmtime(path)

            try:
                if self.last_modified_time[extension] == time:
                    continue
            except KeyError:
                self.last_modified_time[extension] = time

            try:
                await self.bot.reload_extension(extension)
            except commands.ExtensionNotLoaded:
                continue
            except commands.ExtensionError:
                print(f"Couldn't reload extension: {extension}")
            else:
                print(f"Reloaded extension: {extension}")
            finally:
                self.last_modified_time[extension] = time

    @hot_reload_loop.before_loop
    async def cache_last_modified_time(self):
        await self.bot.wait_until_ready()
        self.last_modified_time = {}
        # Mapping = {extension: timestamp}
        for extension in self.bot.extensions.keys():
            if extension in IGNORE_EXTENSIONS:
                continue
            path = path_from_extension(extension)
            time = os.path.getmtime(path)
            self.last_modified_time[extension] = time


async def setup(bot):
    await bot.add_cog(HotReload(bot))
