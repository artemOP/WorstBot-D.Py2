from __future__ import annotations

from typing import TYPE_CHECKING, overload

import discord
import wavelink
from discord import app_commands
from discord.app_commands import Range
from discord.ext import commands

from . import Seek, get_player, humanize_ms

if TYPE_CHECKING:
    from discord import Guild, Interaction, Member, Message, VoiceState
    from wavelink import (
        ExtraEventPayload,
        Player,
        TrackEndEventPayload,
        TrackExceptionEventPayload,
        TrackStartEventPayload,
        TrackStuckEventPayload,
    )

    from WorstBot import Bot

    from . import Segments


@app_commands.guild_only()
class Music(commands.GroupCog, name="music"):
    SponsorBlock = app_commands.Group(
        name="sponsor_block",
        description="Toggle sponsor block segments",
        guild_only=True,
    )

    def __init__(self, bot: Bot):
        self.bot = bot
        self.logger = self.bot.log_handler.getChild(self.qualified_name)

        self.playing: dict[Guild, Message] = {}

    async def cog_load(self) -> None:
        self.logger.info(f"{self.qualified_name} cog loaded")

    async def cog_unload(self) -> None:
        self.logger.info(f"{self.qualified_name} cog unloaded")

    async def interaction_check(self, interaction: Interaction[Bot]) -> bool:
        assert interaction.guild_id
        assert isinstance(interaction.user, discord.Member)
        assert isinstance(interaction.command, app_commands.Command)

        if interaction.command.parent and interaction.command.parent is self.SponsorBlock:
            return True

        if self.bot.config["lavalink"]["enabled"] is False:
            return False
        elif not interaction.user.voice:
            return False

        assert interaction.user.voice.channel

        player = get_player(interaction.guild_id)

        if player is False:
            return False
        elif player is None:
            try:
                player = await interaction.user.voice.channel.connect(cls=wavelink.Player, self_deaf=True)
            except discord.ClientException:
                return False

            player.autoplay = wavelink.AutoPlayMode.partial

            assert player.guild
            segemnts = await self.fetch_segments(player.guild)
            if segemnts:
                await player.node.send(
                    "PUT",
                    path=f"v4/sessions/{player.node.session_id}/players/{player.guild.id}/sponsorblock/categories",
                    data=[key for key, value in segemnts.items() if value is True],
                )

        elif player.channel != interaction.user.voice.channel:
            return False
        interaction.extras["player"] = player
        return True

    async def cog_app_command_error(self, interaction: Interaction, error: Exception):
        if isinstance(error, app_commands.CommandInvokeError):
            error = error.original
        print(type(error))
        match error:
            case app_commands.CheckFailure():
                await interaction.followup.send("Unable to complete this action", ephemeral=True)
            case wavelink.LavalinkLoadException():
                await interaction.followup.send(error.error, ephemeral=True)
            case _:
                raise error

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
        if not (player := get_player(member.guild.id)):
            return

        if all([user.bot for user in player.channel.members]):
            await player.disconnect()

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: TrackStartEventPayload):
        assert payload.player
        assert payload.player.guild

        embed = discord.Embed()  # todo: replace
        try:
            message = await payload.player.channel.send(embed=embed)
        except discord.HTTPException:
            pass
        else:
            self.playing[payload.player.guild] = message

    @overload
    async def on_track_end(self, payload: TrackEndEventPayload) -> None: ...

    @overload
    async def on_track_end(self, payload: TrackStuckEventPayload) -> None: ...

    @overload
    async def on_track_end(self, payload: TrackExceptionEventPayload) -> None: ...

    @commands.Cog.listener("wavelink_track_end")
    @commands.Cog.listener("wavelink_track_exception")
    @commands.Cog.listener("wavelink_track_stuck")
    async def on_track_end(
        self, payload: TrackEndEventPayload | TrackStuckEventPayload | TrackExceptionEventPayload
    ) -> None:
        assert payload.player
        assert payload.player.guild
        message = self.playing[payload.player.guild]
        try:
            await message.delete()
        except discord.HTTPException:
            pass

    @commands.Cog.listener()
    async def on_wavelink_extra_event(self, payload: ExtraEventPayload):
        if not payload.data.get("type", "") == "SegmentSkipped":
            return

        try:
            assert payload.player
            category = payload.data["segment"]["category"]
            time_saved = payload.data["segment"]["end"] - payload.data["segment"]["start"]
            await payload.player.channel.send(
                f"Skipped segment ({category}) saving {humanize_ms(time_saved)}s", delete_after=15
            )
        except:
            pass

    async def reset_player(self, player: Player) -> Player:
        # clear queues
        player.queue.clear()
        player.auto_queue.clear()

        # clear filters
        await player.set_filters()

        # skip current song
        await player.stop()

        return player

    @app_commands.command(name="connect")
    async def connect(self, interaction: Interaction[Bot]):
        """Tell the bot to connect to your current voice channel

        Args:
            interaction (Interaction[Bot]): _description_
        """
        player: Player = interaction.extras["player"]
        await interaction.followup.send(f"Connected to {player.channel.mention}")

    @app_commands.command(name="disconnect")
    async def disconnect(self, interaction: Interaction[Bot]):
        """Tell the bot to disconnect from your current voice channel

        Args:
            interaction (Interaction[Bot]): _description_
        """
        player: Player = interaction.extras["player"]
        await player.disconnect()
        await interaction.followup.send("Disconnected from the voice channel")

    @app_commands.command(name="play")
    async def play(self, interaction: Interaction[Bot], query: str):
        """Search for a song, playlist, album or artist

        Args:
            interaction (Interaction[Bot]): _description_
            query (str): The song to search for
        """
        player: Player = interaction.extras["player"]

        tracks: wavelink.Search = await wavelink.Playable.search(query)
        if not tracks:
            return await interaction.followup.send("No tracks found")

        if isinstance(tracks, wavelink.Playlist):
            map(
                lambda track: setattr(
                    track, "extras", wavelink.ExtrasNamespace({"requester": interaction.user.mention})
                ),
                tracks,
            )
            added: int = await player.queue.put_wait(tracks)
            await interaction.followup.send(f"Added {added} tracks to the queue")
        else:
            track = tracks[0]
            track.extras = {"requester": interaction.user.mention}
            await player.queue.put_wait(track)
            await interaction.followup.send(f"Added {track.title} to the queue")

        if not player.playing:
            await player.play(player.queue.get(), volume=50)

    @app_commands.command(name="pause")
    async def pause(self, interaction: Interaction):
        """Toggle pause/unpause

        Args:
            interaction (Interaction): _description_
        """
        player: Player = interaction.extras["player"]
        await player.pause(not player.paused)
        await interaction.followup.send(f"The player is now {'paused' if player.paused else 'unpaused'}")

    @app_commands.command(name="stop")
    async def stop(self, interaction: Interaction):
        """Stop the currently playing song and clear the queue

        Args:
            interaction (Interaction): _description_
        """
        player: Player = interaction.extras["player"]
        player = await self.reset_player(player)

        await interaction.followup.send("The player has been stopped")

    @app_commands.command(name="skip")
    async def skip(self, interaction: Interaction[Bot]):
        """Skip the current track

        Args:
            interaction (Interaction[Bot]): _description_
        """
        player: Player = interaction.extras["player"]

        await player.skip(force=True)
        await interaction.followup.send("The song has been skipped")

    @app_commands.command(name="move_to")
    async def move_to(self, interaction: Interaction, channel: discord.VoiceChannel):
        """Move the player to a new channel, this will clear the queue.

        Args:
            interaction (Interaction): _description_
            channel (discord.VoiceChannel): _description_
        """
        player: Player = interaction.extras["player"]
        player = await self.reset_player(player)

        await player.move_to(channel)
        await interaction.followup.send(f"player has now moved to {player.channel.mention}")

    @app_commands.command(name="seek")
    async def seek(self, interaction: Interaction, direction: Seek, position: int):
        """Seek the current track

        Args:
            interaction (Interaction): _description_
            direction (SeekType): Skip forwards, backwards or to a specific time
            position (int): The position to seek to
        """
        player: Player = interaction.extras["player"]
        if not player.current:
            return await interaction.followup.send("No track is currently playing", ephemeral=True)
        elif not player.current.is_seekable:
            return await interaction.followup.send("This track is not seekable", ephemeral=True)

        await player.pause(True)
        position = position * 1000
        match direction:
            case Seek.forward:
                await player.seek(player.position + position)
            case Seek.backward:
                await player.seek(player.position - position)
            case Seek.to:
                await player.seek(position)
            case _:
                return await interaction.followup.send("Invalid seek type", ephemeral=True)

        await player.pause(False)
        new_position = humanize_ms(player.position)
        await interaction.followup.send(f"Seeked to {new_position}", ephemeral=True)

    @app_commands.command(name="volume")
    async def volume(self, interaction: Interaction, volume: Range[int, 1, 1000]):
        """Set the volume of the player

        Args:
            interaction (Interaction): _description_
            volume (int): The volume to set, 1-1000 (can be distorted past 100)
        """
        player: Player = interaction.extras["player"]
        await player.set_volume(volume)
        await interaction.followup.send(f"Volume set to {volume}")

    @app_commands.command(name="shuffle")
    async def shuffle(self, interaction: Interaction):
        """Shuffle the queue

        Args:
            interaction (Interaction): _description_
        """
        player: Player = interaction.extras["player"]
        player.queue.shuffle()
        player.auto_queue.shuffle()
        await interaction.followup.send("Queue has been shuffled")

    @app_commands.command(name="loop")
    async def loop(self, interaction: Interaction, mode: wavelink.QueueMode):
        """Set the loop mode

        Args:
            interaction (Interaction): _description_
            mode (Repeat): The loop mode
        """
        player: Player = interaction.extras["player"]
        player.queue.mode = mode
        await interaction.followup.send(f"Loop mode set to {mode.name}")

    @app_commands.command(name="current")
    async def current_song(self, interaction: Interaction):
        """Get the current song

        Args:
            interaction (Interaction): _description_
        """
        player: Player = interaction.extras["player"]
        playing = player.current

        if not playing:
            return await interaction.followup.send("No track is currently playing", ephemeral=True)

    @app_commands.command(name="queue")
    async def queue(self, interaction: Interaction):
        """View the current queue

        Args:
            interaction (Interaction): _description_
        """
        ...

    @app_commands.command(name="auto-queue")
    async def auto_queue(self, interaction: Interaction):
        """View the suggestions queue

        Args:
            interaction (Interaction): _description_
        """
        ...

    @app_commands.command(name="history")
    async def history(self, interaction: Interaction):
        """Get the history of the player

        Args:
            interaction (Interaction): _description_
        """
        ...

    @app_commands.command(name="autoplay")
    async def autoplay(self, interaction: Interaction):
        """Toggle autoplay suggested content

        Args:
            interaction (Interaction): _description_
        """
        player: Player = interaction.extras["player"]
        if player.autoplay == wavelink.AutoPlayMode.partial:
            player.autoplay = wavelink.AutoPlayMode.enabled
            await interaction.followup.send(
                "Autoplay enabled, you will start receiving suggested videos when the queue ends"
            )
        else:
            player.autoplay = wavelink.AutoPlayMode.partial
            await interaction.followup.send("Autoplay disabled")

    async def fetch_segments(self, guild: Guild) -> Segments | None:
        segments: Segments = await self.bot.pool.fetchrow("SELECT * FROM sponsor_block WHERE guild_id = $1", guild.id)
        return segments

    async def set_segments(self, segments: Segments) -> None:
        await self.bot.pool.execute(
            "INSERT INTO sponsor_block VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9) ON CONFLICT (guild_id) DO UPDATE SET sponsor=EXCLUDED.sponsor, selfpromo=EXCLUDED.selfpromo, interaction=EXCLUDED.interaction, intro=EXCLUDED.intro, outro=EXCLUDED.outro, preview=EXCLUDED.preview, music_offtopic=EXCLUDED.music_offtopic, filler=EXCLUDED.filler",
            *segments.values(),
        )

    def format_segments(self, segments: Segments) -> str:
        return "".join(f"{key}: {value}\n" for key, value in segments.items())

    @SponsorBlock.command(name="set")
    @app_commands.rename(_interaction="interaction")
    async def toggle_segments(
        self,
        interaction: Interaction,
        sponsor: bool = True,
        self_promo: bool = True,
        _interaction: bool = True,
        intro: bool = True,
        outro: bool = True,
        preview: bool = True,
        music_offtopic: bool = True,
        filler: bool = False,
    ):
        """Toggle segments to automatically skip, updates when the player is first connected

        Args:
            interaction (Interaction): _description_
            sponsor (bool, optional): Skip sponsor segments. Defaults to True.
            self_promo (bool, optional): Skip self promotion segments. Defaults to True.
            _interaction (bool, optional): Skip interaction reminders. Defaults to True.
            intro (bool, optional): Skip intros. Defaults to True.
            outro (bool, optional): Skip outros. Defaults to True.
            preview (bool, optional): Skip previews. Defaults to True.
            music_offtopic (bool, optional): Skip off topic music. Defaults to True.
            filler (bool, optional): Skip filler. Defaults to False.
        """
        assert interaction.guild_id
        segments: Segments = {
            "guild": interaction.guild_id,
            "sponsor": sponsor,
            "selfpromo": self_promo,
            "interaction": _interaction,
            "intro": intro,
            "outro": outro,
            "preview": preview,
            "music_offtopic": music_offtopic,
            "filler": filler,
        }
        await self.set_segments(segments)
        await interaction.followup.send(f"Segments set to:\n{self.format_segments(segments)}")

    @SponsorBlock.command(name="view")
    async def view_segments(self, interaction: Interaction):
        """View the current SponsorBlock configuration

        Args:
            interaction (Interaction): _description_

        Returns:
            _type_: _description_
        """
        assert interaction.guild
        segments = await self.fetch_segments(interaction.guild)
        if not segments:
            return await interaction.followup.send("No segments set")
        await interaction.followup.send(f"Segments set to:\n{self.format_segments(segments)}")


async def setup(bot: Bot):
    await bot.add_cog(Music(bot))
