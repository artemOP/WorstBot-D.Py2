from __future__ import annotations

from typing import TYPE_CHECKING

from .....core.utils import paginators
from .._enums import GameState

if TYPE_CHECKING:
    from .. import GameManager, Player


class Game(paginators.BaseView):
    def __init__(self, game: GameManager, player: Player):
        super().__init__(timeout=10 * 60)
        self.game: GameManager = game
        self.player: Player = player

    async def on_timeout(self) -> None:
        self.game.state = GameState.cancelled
        for player in self.game.players:
            if not player.view:
                continue
            await player.view.response.edit(
                view=None, embed=None, content="The game has been cancelled due to inactivity"
            )
            player.view.stop()
