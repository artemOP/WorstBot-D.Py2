import discord
from discord.ext import commands
import Tokens
from os import listdir
import asyncpg
import datetime

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

    @staticmethod
    async def fetch(sql: str, *args):
        async with bot.pool.acquire() as conn:
            async with conn.transaction():
                return await conn.fetch(sql, *args)

    @staticmethod
    async def fetchrow(sql: str, *args):
        async with bot.pool.acquire() as conn:
            async with conn.transaction():
                return await conn.fetchrow(sql, *args)

    @staticmethod
    async def fetchval(sql: str, *args):
        async with bot.pool.acquire() as conn:
            async with conn.transaction():
                return await conn.fetchval(sql, *args)

    @staticmethod
    async def execute(sql: str, *args):
        async with bot.pool.acquire() as conn:
            async with conn.transaction():
                return await conn.fetchval(sql, *args)


intents = discord.Intents.all()
bot = WorstBot(command_prefix = commands.when_mentioned_or('.'),
               activity = discord.Game(name = "With ones and zeros"),
               intents = intents)
bot.run(Tokens.discord)
