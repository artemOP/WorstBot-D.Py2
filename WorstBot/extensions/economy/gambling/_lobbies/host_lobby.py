from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import ui

from .._enums import PlayerState
from .lobby import Lobby

if TYPE_CHECKING:
    from discord import Interaction

    from WorstBot import Bot

    from .. import GameManager, Player


class HostLobby(Lobby):
    def __init__(self, game: GameManager, player: Player):
        super().__init__(game, player)

    @ui.button(label="Start", style=discord.ButtonStyle.green)
    async def start(self, interaction: Interaction[Bot], button: ui.Button):
        if all(player.state is PlayerState.ready for player in self.game.players):
            await interaction.response.defer()
            await self.game.start(interaction)
            self.stop()
        else:
            await interaction.response.send_message("Not all players are ready", ephemeral=True)

    @ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: Interaction[Bot], button: ui.Button):
        await self.game.cancel(interaction)
        self.stop()
