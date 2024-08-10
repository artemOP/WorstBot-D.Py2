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
