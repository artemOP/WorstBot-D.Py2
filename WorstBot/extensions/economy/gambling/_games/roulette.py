from __future__ import annotations

from typing import TYPE_CHECKING

from .._types import ROULETTE_NUMBERS
from .._enums import RouletteBets, RouletteColours
from .game import Game

if TYPE_CHECKING:
    from .. import GameManager, Player


class Roulette(Game): ...
