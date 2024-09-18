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


class GuestLobby(Lobby):
    def __init__(self, game: GameManager, player: Player):
        super().__init__(game, player)

    @ui.button(label="ready", style=discord.ButtonStyle.green)
    async def ready(self, interaction: Interaction[Bot], button: ui.Button):
        self.player.state = PlayerState.ready
        button.disabled = True
        await interaction.response.edit_message(view=self)

    @ui.button(label="exit", style=discord.ButtonStyle.red)
    async def exit(self, interaction: Interaction[Bot], button: ui.Button):
        await self.game.remove_player(self.player.wealth)
        await interaction.response.edit_message(view=None, embed=None, content="You have left the lobby")
        self.stop()
