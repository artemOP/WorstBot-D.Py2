import discord
from discord.ext import commands
import Tokens
from os import listdir
import asyncpg
import datetime
import logging

logging.basicConfig(level = logging.INFO)


class WorstBot(commands.Bot):
    def __init__ (self, command_prefix, activity, intents):
        super().__init__(command_prefix, intents = intents)
        self.activity = activity

    async def setup_hook (self) -> None:
        for filename in listdir("cogs"):
            if filename.endswith(".py"):
                await bot.load_extension(f'cogs.{filename[:-3]}')
                pass
        bot.pool = await asyncpg.create_pool(database = "WorstDB", user = "WorstBot", password = Tokens.postgres, command_timeout = 10, max_size = 100, min_size = 25)

    async def on_ready (self):
        alpha = discord.Object(id = 700833272380522496)
        nerds = discord.Object(id = 431538712367726592)
        bot.tree.clear_commands(guild = alpha)
        bot.tree.copy_global_to(guild = alpha)
        await bot.tree.sync(guild = alpha)
        print(f"Connected as {self.user} at {datetime.datetime.now().strftime('%d/%m/%y %H:%M')}")


intents = discord.Intents.all()
bot = WorstBot(command_prefix = commands.when_mentioned_or('.'),
               activity = discord.Game(name = "With ones and zeros"),
               intents = intents)
bot.run(Tokens.discord)

# TODO:CREATE DB TABLE FORMAT GUILD ID, COMMAND1,2,3... WITH BOOL VALUES TO DETERMINE IF ENABLED OR NOT, USE app_commands.check  TO DETERMINE STATE AND ONLY RUN IF TRUE
