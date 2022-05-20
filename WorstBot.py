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
        bot.fetch = self.fetch
        bot.fetchrow = self.fetchrow
        bot.fetchval = self.fetchval
        bot.execute = self.execute

    async def on_ready (self):
        alpha = discord.Object(id = 700833272380522496)
        nerds = discord.Object(id = 431538712367726592)
        bot.tree.clear_commands(guild = alpha)
        bot.tree.copy_global_to(guild = alpha)
        await bot.tree.sync(guild = alpha)
        print(f"Connected as {self.user} at {datetime.datetime.now().strftime('%d/%m/%y %H:%M')}")

    async def fetch(self, sql: str, *args):
        async with bot.pool.acquire() as conn:
            async with conn.transaction():
                return await conn.fetch(sql, *args)

    async def fetchrow(self, sql: str, *args):
        async with bot.pool.acquire() as conn:
            async with conn.transaction():
                return await conn.fetchrow(sql, *args)

    async def fetchval(self, sql: str, *args):
        async with bot.pool.acquire() as conn:
            async with conn.transaction():
                return await conn.fetchval(sql, *args)

    async def execute(self, sql: str, *args):
        async with bot.pool.acquire() as conn:
            async with conn.transaction():
                return await conn.fetchval(sql, *args)


intents = discord.Intents.all()
bot = WorstBot(command_prefix = commands.when_mentioned_or('.'),
               activity = discord.Game(name = "With ones and zeros"),
               intents = intents)
bot.run(Tokens.discord)

# TODO:CREATE DB TABLE FORMAT GUILD ID, COMMAND1,2,3... WITH BOOL VALUES TO DETERMINE IF ENABLED OR NOT, USE app_commands.check  TO DETERMINE STATE AND ONLY RUN IF TRUE
