import discord
from discord import app_commands
from discord.ext import commands

@app_commands.default_permissions()
class StickyMessage(commands.GroupCog, name = "sticky"):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    async def cog_load(self) -> None:
        await self.bot.execute("CREATE TABLE IF NOT EXISTS sticky(channel BIGINT UNIQUE NOT NULL,messageid BIGINT, message TEXT NOT NULL )")

    async def cog_unload(self) -> None:
        ...

    @commands.Cog.listener()
    async def on_ready(self):
        print("StickyMessage cog online")

    @app_commands.command(name = "add", description = "Pin a message to the bottom of a channel")
    async def StickyAdd(self, interaction: discord.Interaction, message: str):
        await self.bot.execute("INSERT INTO sticky(channel, messageid, message) VALUES($1, $2, $3) ON CONFLICT (channel) DO UPDATE SET messageid=NULL , message=excluded.message", interaction.channel_id, None, message)
        await interaction.response.send_message(f'"{message}" \n\nhas been added as a sticky.', ephemeral = True)

    @app_commands.command(name = "remove", description = "Remove pinned message")
    async def StickyRemove(self, interaction: discord.Interaction):
        await self.bot.execute("DELETE FROM sticky WHERE channel=$1", interaction.channel_id)
        await interaction.response.send_message('Sticky has been removed from this channel.', ephemeral = True)

    @commands.Cog.listener()
    async def on_message(self, message):
        sticky = await self.bot.fetchval("SELECT EXISTS( SELECT 1 FROM sticky WHERE channel = $1)", message.channel.id)
        if message.author.bot or not sticky:
            return
        sticky = await self.bot.fetchrow("SELECT * FROM sticky WHERE channel=$1", message.channel.id)
        if sticky["messageid"]:
            try:
                oldmessage = await message.channel.fetch_message(sticky["messageid"])
            except:
                oldmessage = await message.channel.fetch_message(message.channel.last_message_id)
            await oldmessage.delete()
        sticky = await message.channel.send(sticky["message"])
        await self.bot.execute("UPDATE sticky SET messageid=$1 WHERE channel=$2", sticky.id, message.channel.id)


async def setup(bot):
    await bot.add_cog(StickyMessage(bot))
