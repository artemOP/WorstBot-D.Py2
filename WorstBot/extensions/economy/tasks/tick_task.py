from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import ui

from .. import Transactions, payout
from .embeds import Punish, Reward
from .task import Task

if TYPE_CHECKING:
    from discord import Interaction

    from WorstBot import Bot

    from .. import Wealth


class TickTask(Task):
    def __init__(self, wealth: Wealth):
        super().__init__(wealth, timeout=30)

    @ui.button(emoji="\U00002705", style=discord.ButtonStyle.green, row=0)
    async def tick(self, interaction: Interaction[Bot], button: ui.Button):
        self.stop()
        embed = Reward(self.wealth, self.amount)
        await payout(interaction.client, self.wealth, Transactions.work, self.amount * self.wealth.multiplier)
        await interaction.response.edit_message(view=None, embed=embed)

    @ui.button(emoji="\U0000274c", style=discord.ButtonStyle.red, row=0)
    async def cross(self, interaction: Interaction[Bot], button: ui.Button):
        self.stop()
        embed = Punish(self.amount)
        await payout(interaction.client, self.wealth, Transactions.work, -self.amount)
        await interaction.response.edit_message(view=None, embed=embed)
