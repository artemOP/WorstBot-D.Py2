from __future__ import annotations

from typing import TYPE_CHECKING

from .....core.utils import paginators

if TYPE_CHECKING:
    from .. import GameManager, Player


class Lobby(paginators.BaseView):
    def __init__(self, game: GameManager, player: Player):
        super().__init__(timeout=10 * 60)
        self.game: GameManager = game
        self.player: Player = player
