from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ui import Button

from .. import Transactions, payout
from .embeds import Punish, Reward
from .task import Task

if TYPE_CHECKING:
    from discord import Interaction

    from WorstBot import Bot

    from .. import Wealth


class KeypadTask(Task):
    def __init__(self, wealth: Wealth, code: list[str]):
        super().__init__(wealth, timeout=30)
        self.code = code
        self.buttons: dict[str, Button] = {}
        for i in range(1, 10):
            custom_id = f"{wealth.member.id}:{i}"
            button = Button(label=str(i), style=discord.ButtonStyle.gray, row=(i - 1) // 3, custom_id=custom_id)
            button.callback = self.button_callback
            self.add_item(button)
            self.buttons[custom_id] = button

    async def button_callback(self, interaction: Interaction[Bot]):
        button = self.buttons[interaction.data["custom_id"]]  # type: ignore
        if button.label != self.code[0]:
            self.stop()
            embed = Punish(self.amount)
            return await interaction.response.edit_message(view=None, embed=embed)

        button.style = discord.ButtonStyle.green
        button.disabled = True
        self.code.pop(0)

        if self.code:
            return await interaction.response.edit_message(view=self)

        self.stop()
        embed = Reward(self.wealth, self.amount)
        await payout(interaction.client, self.wealth, Transactions.work, self.amount * self.wealth.multiplier)
        await interaction.response.edit_message(view=None, embed=embed)
