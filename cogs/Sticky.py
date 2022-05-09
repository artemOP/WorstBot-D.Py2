from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands

class StickyMessage(commands.Cog, app_commands.Group,name="sticky"):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("CREATE TABLE IF NOT EXISTS Sticky(channel BIGINT UNIQUE NOT NULL,messageid BIGINT, message TEXT NOT NULL )")
        print("BaseEvents cog online")

    @app_commands.command(name="add", description = "Pin a message to the bottom of a channel")
    @app_commands.default_permissions(manage_messages = True)
    async def StickyAdd(self,interaction:discord.Interaction, message:str):
        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("INSERT INTO Sticky(channel, messageid, message) VALUES($1, $2, $3) ON CONFLICT (channel) DO UPDATE SET messageid=NULL , message=EXCLUDED.message", interaction.channel_id, None, message)
        await interaction.response.send_message(f'"{message}" \n\nhas been added as a sticky.')

    @app_commands.command(name = "remove", description = "Remove pinned message")
    @app_commands.default_permissions(manage_messages = True)
    async def StickyRemove(self, interaction: discord.Interaction):
        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("DELETE FROM Sticky WHERE channel=$1", interaction.channel_id)
        await interaction.response.send_message('Sticky has been removed from this channel.')

    @commands.Cog.listener()
    async def on_message(self, message):
        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                sticky = await conn.fetchval("SELECT EXISTS( SELECT 1 FROM Sticky WHERE channel = $1)", message.channel.id)

        if message.author.bot or not sticky:
            return

        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                sticky = await conn.fetchrow("SELECT * from Sticky where channel=$1", message.channel.id)

        if sticky["messageid"]:
            try:
                oldmessage = await message.channel.fetch_message(sticky["messageid"])
            except:
                oldmessage = await message.channel.fetch_message(message.channel.last_message_id)
            await oldmessage.delete()

        sticky = await message.channel.send(sticky["message"])
        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("UPDATE Sticky SET messageid=$1 WHERE channel=$2", sticky.id, message.channel.id)

async def setup(bot):
    await bot.add_cog(StickyMessage(bot))
