from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import Colour, Embed

if TYPE_CHECKING:
    from . import Wealth


class Leaderboard(Embed): ...


class Balance(Embed): ...


class KeypadTask(Embed):
    def __init__(self, code: list[str]):
        super().__init__(
            title="Keypad Task",
            description=f"Please enter the following code in the correct order:\n {",".join(code)}",
            colour=Colour.random(),
        )


class CountingTask(Embed): 
    def __init__(self):
        super().__init__(title="Learning 2 count", description="Show off your counting skills", colour=Colour.random())


class TickTask(Embed): 
    def __init__(self):
        super().__init__(title="Tick Task", description="Click the tick to complete the task", colour=Colour.random())
