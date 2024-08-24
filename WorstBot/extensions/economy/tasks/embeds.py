from __future__ import annotations

from typing import TYPE_CHECKING

from discord import Colour, Embed

if TYPE_CHECKING:
    from .. import Wealth


class Reward(Embed):
    def __init__(self, user: Wealth, amount: int):
        super().__init__(
            title="Task Complete",
            description=f"Task Successful, W${amount * user.multiplier} has been added to your wallet",
            colour=Colour.random(),
        )


class Punish(Embed):
    def __init__(self, amount: int):
        super().__init__(
            title="Task Complete",
            description=f"Task Failed, W${amount} has been removed from your wallet",
            colour=Colour.random(),
        )


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
