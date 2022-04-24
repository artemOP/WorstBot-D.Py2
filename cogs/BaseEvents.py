import discord
from discord import app_commands
from discord.ext import commands

class BaseEvents(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("BaseEvents cog online")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                roles = await conn.fetchall("SELECT role FROM Autorole WHERE guild=$1", member.guild.id)

async def setup(bot):
    await bot.add_cog(BaseEvents(bot))
