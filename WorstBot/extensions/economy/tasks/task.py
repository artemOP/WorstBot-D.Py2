from __future__ import annotations

from random import randint
from typing import TYPE_CHECKING

from ....core.utils.paginators import BaseView

if TYPE_CHECKING:
    from .. import Wealth


class Task(BaseView):
    def __init__(self, wealth: Wealth, amount: int | None = None, timeout: int = 60):
        super().__init__(timeout=timeout)
        self.wealth = wealth
        self.amount = amount or randint(150, 1500)
