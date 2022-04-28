from datetime import datetime
import discord
from discord import app_commands
from discord.ext import commands, tasks
from typing import Optional

class Opinion(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.DeleteOld.start()
        self.prefixes = [":", ".", "!", "?", "/", ">", "+", '"']

    @commands.Cog.listener()
    async def on_ready(self):
        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("CREATE TABLE IF NOT EXISTS Opinion(guild BIGINT NOT NULL, timestamp TIMESTAMP WITH TIME ZONE NOT NULL, content TEXT DEFAULT NULL, attachment TEXT DEFAULT NULL)")
        print("Opinion cog online")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot is False and message.channel.is_nsfw() is False:
            if not any(message.content.startswith(prefix) for prefix in self.prefixes):
                if message.attachments:
                    message.attachments = str(message.attachments[-1])
                else:
                    message.attachments = ""
                async with self.bot.pool.acquire() as conn:
                    async with conn.transaction():
                        await conn.execute("INSERT INTO Opinion(guild, timestamp, content, attachment) VALUES ($1,$2,$3,$4)",
                                           message.guild.id, message.created_at, message.clean_content, message.attachments)

    @app_commands.command(name="opinion", description="Ask worst bot for its opinion on your super important questions")
    async def opinion(self,interaction:discord.Interaction, opinion:str=None):
        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetch("SELECT content, attachment FROM Opinion WHERE GUILD=$1 ORDER BY random() LIMIT 1", interaction.guild.id)
        await interaction.response.send_message(content=f"""{row[0]["content"]}\n{row[0]["attachment"]}""")

    @tasks.loop(hours=24, reconnect=True)
    async def DeleteOld(self):
        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("DELETE FROM opinion WHERE timestamp < CURRENT_TIMESTAMP - INTERVAL '2 weeks'")

    @DeleteOld.before_loop
    async def BeforeDeleteOld(self):
        await self.bot.wait_until_ready()



async def setup(bot):
    await bot.add_cog(Opinion(bot))
