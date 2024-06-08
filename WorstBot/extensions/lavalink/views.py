from __future__ import annotations

from typing import TYPE_CHECKING, Any

import discord
from discord.ui import Button

from WorstBot.core.utils import paginators

from . import utils

if TYPE_CHECKING:
    from discord import Interaction
    from discord.ui import Button

    from WorstBot import Bot

    from . import Segments


class Config(paginators.BaseView):
    def __init__(self, segments: Segments, *, timeout: float | None = 180):
        super().__init__(timeout=timeout)
        self.segments = segments

        for name, value in segments.items():
            if not isinstance(value, bool):
                continue

            style = discord.ButtonStyle.green if value else discord.ButtonStyle.red
            button = ConfigButton(label=name, style=style)
            self.add_item(button)


class ConfigButton(Button):
    def __init__(self, label: str, style: discord.ButtonStyle):
        super().__init__(label=label, style=style)

    async def callback(self, interaction: Interaction[Bot]) -> Any:
        assert isinstance(self.view, Config)
        assert self.label
        assert interaction.guild_id

        value = False if self.style == discord.ButtonStyle.green else True
        self.view.segments[self.label] = value

        print(self.label, value)

        await utils.set_segments(interaction, self.view.segments)

        self.style = discord.ButtonStyle.green if value else discord.ButtonStyle.red
        await interaction.response.edit_message(view=self.view)
