import discord
from discord import Interaction, app_commands
from discord.ext import commands, tasks
from os import environ
from asyncio import sleep

@app_commands.default_permissions()
class Twitch(commands.GroupCog, name = "twitch"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.TwitchClientId = environ.get("twitch_client")
        self.TwitchSecret = environ.get("twitch_secret")
        self.token = None
        self.streamersTable = None

        self.request.start()

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.execute("CREATE TABLE IF NOT EXISTS twitch(guild BIGINT NOT NULL, channel BIGINT NOT NULL, userid BIGINT NOT NULL, live BOOLEAN NOT NULL DEFAULT FALSE, UNIQUE(guild, userid))")
        await self.TokenGen()
        await self.streamers()
        print("Twitch cog online")

    async def streamers(self):
        self.streamersTable = await self.bot.fetch("SELECT * FROM twitch")

    async def validate(self, token: int):
        validity = await self.bot.get(url = "https://id.twitch.tv/oauth2/validate", headers = {"Authorization": f"Bearer {token}"})
        if validity["status"] == 200:
            return True
        await self.TokenGen()

    async def TokenGen(self):
        token = await self.bot.post(url = "https://id.twitch.tv/oauth2/token",
                                    params = {
                                        "client_id": self.TwitchClientId,
                                        "client_secret": self.TwitchSecret,
                                        "grant_type": "client_credentials"
                                    }
                                    )
        self.token = token["access_token"]

    @app_commands.command(name = "add", description = "Get live alerts for your selected twitch channel")
    async def LiveTrackingAdd(self, interaction: Interaction, channel: discord.TextChannel, twitch_user: str):
        twitch_user = await self.bot.to_int(twitch_user)
        await self.bot.execute("INSERT INTO twitch(guild, channel, userid) VALUES($1, $2, $3) ON CONFLICT (guild, userid) DO NOTHING", interaction.guild_id, channel.id, twitch_user)
        await self.streamers()
        await interaction.response.send_message("Streamer has been added to the Tracking list", ephemeral = True)

    @app_commands.command(name = "remove", description = "Remove live alerts from your selected channel")
    async def LiveTrackingRemove(self, interaction: Interaction, twitch_user: str):
        twitch_user = await self.bot.to_int(twitch_user)
        await self.bot.execute("DELETE FROM twitch WHERE userid=$1", twitch_user)
        await self.streamers()
        await interaction.response.send_message("Streamer has been removed from the Tracking list", ephemeral = True)

    @LiveTrackingAdd.autocomplete("twitch_user")
    async def LiveTrackingAddAutocomplete(self, interaction: Interaction, current):
        if not await self.validate(self.token):
            return []
        if len(current) < 3:
            return []
        responses = await self.bot.get(url = "https://api.twitch.tv/helix/search/channels", params = {"query": current, "first": 25}, headers = {"client-id": self.TwitchClientId, "Authorization": "Bearer " + self.token})
        return [app_commands.Choice(name = response["display_name"], value = response["id"]) for response in responses["data"]]

    @LiveTrackingRemove.autocomplete("twitch_user")
    async def LiveTrackingRemoveAutocomplete(self, interaction: Interaction, current):
        if not await self.validate(self.token):
            return []
        streamIDs = await self.bot.fetch("SELECT userid FROM twitch WHERE guild=$1 LIMIT 25", interaction.guild_id)
        if not streamIDs:
            return []
        streamers = await self.bot.get(url = "https://api.twitch.tv/helix/channels", params = {"broadcaster_id": [streamID["userid"] for streamID in streamIDs]}, headers = {"client-id": self.TwitchClientId, "Authorization": "Bearer " + self.token})
        return [app_commands.Choice(name = streamer["broadcaster_name"], value = streamer["broadcaster_id"]) for streamer in streamers["data"]]

    @tasks.loop(minutes = 1, reconnect = True)
    async def request(self):
        if not await self.validate(self.token):
            return
        streams = await self.bot.get(url = "https://api.twitch.tv/helix/streams", params = {"user_id": [user["userid"] for user in self.streamersTable]}, headers = {"client-id": self.TwitchClientId, "Authorization": "Bearer " + self.token})
        if not streams["data"]:
            return
        for user in self.streamersTable:
            if not any(int(stream["user_id"]) == user["userid"] for stream in streams["data"]):
                await self.bot.execute("UPDATE twitch SET live = FALSE WHERE userid = $1", user["userid"])
                continue
            if await self.bot.fetchval("SELECT live FROM twitch WHERE userid=$1", user["userid"]) is True:
                continue
            await self.bot.execute("UPDATE twitch SET live = TRUE WHERE userid=$1", user["userid"])
            stream = [dictionary for dictionary in streams["data"] if int(dictionary["user_id"]) == user["userid"]][0]
            channel = self.bot.get_channel(user["channel"])
            embed = discord.Embed(colour = discord.Colour.random(), title = stream["user_name"])
            embed.description = f"""{stream["user_name"]} just went live on twitch!\n{stream["title"]}\nfind them at https://www.twitch.tv/{stream["user_name"]}"""
            embed.set_thumbnail(url = stream["thumbnail_url"])
            embed.set_footer(text = stream["started_at"].split("T")[1].split("Z")[0])
            await channel.send(embed=embed, content = "@everyone")

    @request.before_loop
    async def before_my_task(self):
        await self.bot.wait_until_ready()
        await sleep(3)

async def setup(bot):
    await bot.add_cog(Twitch(bot))
