import discord
from discord import app_commands
from discord.ext import commands
import discord.utils
from asyncio import sleep

class PersonalCalls(commands.Cog):
    def __init__(self,bot):
        self.bot=bot

    @commands.Cog.listener()
    async def on_ready(self):
        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("CREATE TABLE IF NOT EXISTS PersonalCall(guild BIGINT UNIQUE, channel BIGINT UNIQUE)")
                await conn.execute("CREATE TABLE IF NOT EXISTS CallBlacklist(guild BIGINT, channel BIGINT)")
                await conn.execute("CREATE TABLE IF NOT EXISTS UserBlacklist(member BIGINT UNIQUE)")
        print("Personal call cog online")

    async def fetchval(self,sql:str,args:list):
        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                return await conn.fetchval(sql, *args)

    @commands.Cog.listener()
    async def on_voice_state_update(self,member, before, after):
        PersonalChannel = self.bot.get_channel(self.fetchval("SELECT channel FROM PersonalCall WHERE guild=$1", [member.guild.id]))
        if await self.fetchval("SELECT EXISTS(SELECT 1 FROM UserBlacklist WHERE member=$1)",[member.id]) and after.channel is not None:
            if after.channel.id == PersonalChannel.id:
                await member.edit(voice_channel=None)
                return
        if before.channel is None and after.channel is not None:
            if after.channel.id ==  PersonalChannel.id:
                channel = await after.category(name=member.name, user_limit=99, bitrate = member.guild.bitrate_limit)
                await member.move_to(channel)
        elif before.channel is not None and before.channel.id != PersonalChannel.id:
            if self.fetchval("SELECT EXISTS(SELECT 1 FROM CallBlacklist WHERE channel=$1)",[before.id]) and before.channel.members ==[]:
                await before.channel.delete()
        if after.channel is not None and after.channel.id == PersonalChannel.id:
            await member.edit(voice_channel=None)



async def setup(bot):
    await bot.add_cog(PersonalCalls(bot))
