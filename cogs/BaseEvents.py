from discord.ext import commands

class BaseEvents(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("BaseEvents cog online")

async def setup(bot):
    await bot.add_cog(BaseEvents(bot))
