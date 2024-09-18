from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

from ._games import Game
from ._lobbies import Lobby
from ._enums import PlayerState

if TYPE_CHECKING:
    from .. import Wealth


class Player:
    def __init__(self, wealth: Wealth, bet: float | int, state: PlayerState = PlayerState.unready) -> None:
        self._wealth: Wealth = wealth
        self._bet: float | int = bet
        self.state: PlayerState = state
        self.view: Game | Lobby | None = None

    __slots__ = ("_wealth", "_bet", "state", "view")

    @property
    def wealth(self) -> Wealth:
        return self._wealth

    @property
    def bet(self) -> float | int:
        return self._bet

    def __hash__(self) -> int:
        return self.wealth.__hash__()

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, self.__class__):
            return False
        return self.wealth == o.wealth
