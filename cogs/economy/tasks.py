from __future__ import annotations
from random import sample, randint, choice

import discord
from discord import app_commands, Interaction, ui
from discord.ext import commands

from WorstBot import WorstBot
from modules import Paginators, EmbedGen
from ._utils import Wealth, get_wealth

class Task(Paginators.BaseView):
    def __init__(self, wealth: Wealth, amount: int = None, timeout: int = 30):
        super().__init__(timeout = timeout)
        self.wealth = wealth
        self.amount = amount or randint(150, 1500)

class KeypadTask(Task):
    def __init__(self, wealth: Wealth, code: list[str]):
        super().__init__(wealth, timeout = 30)
        self.code = code
        self.buttons = {}
        for i in range(1, 10):
            custom_id = f"{wealth.member_id}:{i}"
            button = ui.Button(label = str(i), style = discord.ButtonStyle.gray, row = (i - 1) // 3, custom_id = custom_id)
            button.callback = self.button_callback
            self.add_item(button)
            self.buttons[custom_id] = button

    async def button_callback(self, interaction: Interaction):
        button = self.buttons[interaction.data["custom_id"]]
        if button.label != self.code[0]:
            self.stop()
            return await interaction.response.edit_message(view = None, embed = None, content = "Task Failed, please learn to count")

        button.style = discord.ButtonStyle.green
        button.disabled = True
        self.code.pop(0)

        if self.code:
            return await interaction.response.edit_message(view = self)

        self.stop()
        embed = EmbedGen.SimpleEmbed(
            title = "Task Complete",
            text = f"Task Successful, W${self.amount * self.wealth.multiplier} has been added to your wallet",
        )
        await self.wealth.reward(interaction.client, self.amount, use_multiplier = True)
        await interaction.response.edit_message(view = None, embed = embed)

class TickTask(Task):
    def __init__(self, wealth: Wealth):
        super().__init__(wealth, timeout = 30)

    @ui.button(emoji = "\U00002705", style = discord.ButtonStyle.green, row = 0)
    async def tick(self, interaction: Interaction, button: ui.Button):
        await self.wealth.reward(interaction.client, self.amount, use_multiplier = True)
        await interaction.response.edit_message(view = None, embed = None, content = f"Task Successful, W${self.amount * self.wealth.multiplier} has been added to your wallet")
        self.stop()

    @ui.button(emoji = "\U0000274c", style = discord.ButtonStyle.red, row = 0)
    async def cross(self, interaction: Interaction, button: ui.Button):
        await self.wealth.punish(interaction.client, self.amount)
        await interaction.response.edit_message(view = None, embed = None, content = f"Task Failed, W${self.amount} has been removed from your wallet")
        self.stop()

class Tasks(commands.Cog):

    def __init__(self, bot: WorstBot):
        self.bot = bot
        self.logger = bot.logger.getChild(self.qualified_name)
        self.tasks = [self.tick_task, self.keypad_task, self.counting]

    async def cog_load(self) -> None:
        self.logger.info(f"{self.qualified_name} cog loaded")

    async def cog_unload(self) -> None:
        self.logger.info(f"{self.qualified_name} cog unloaded")

    async def keypad_task(self, interaction: Interaction, user: Wealth) -> Task:
        code = sample([str(i) for i in range(1, 10)], k = 9)
        embed = EmbedGen.SimpleEmbed(
            title = "Keypad Task",
            text = f"Please enter the folowing code in the correct order:\n {', '.join(code)}",
        )
        view = KeypadTask(user, code)
        await interaction.response.send_message(view = view, embed = embed, ephemeral = True)
        view.response = await interaction.original_response()
        return view

    async def counting(self, interaction: Interaction, user: Wealth) -> Task:
        embed = EmbedGen.SimpleEmbed(
            title = "Learning 2 count",
            text = "Show off your counting skills!",
        )
        view = KeypadTask(user, [str(i) for i in range(1, 10)])
        await interaction.response.send_message(view = view, embed = embed, ephemeral = True)
        view.response = await interaction.original_response()
        return view

    async def tick_task(self, interaction: Interaction, user: Wealth) -> Task:
        embed = EmbedGen.SimpleEmbed(
            title = "Tick Task",
            text = "Click the tick to complete the task",
        )
        view = TickTask(user)
        await interaction.response.send_message(view = view, embed = embed, ephemeral = True)
        view.response = await interaction.original_response()
        return view

    @app_commands.command(name = "work")
    @app_commands.checks.cooldown(1, 60*60, key = lambda i: (i.guild_id, i.user.id))
    @app_commands.guild_only()
    async def work(self, interaction: Interaction):
        """Complete a task to earn money

        :param interaction:
        :return:
        """
        user = await get_wealth(self.bot, interaction.guild, interaction.user)
        view: Task = await choice(self.tasks)(interaction, user)
        await view.wait()
        await self.bot.execute("INSERT INTO transactions(user_id, recipient, amount, timestamp) VALUES ($1, 'work', $2, now()::timestamptz)", user.member_id, view.amount)

async def setup(bot):
    await bot.add_cog(Tasks(bot))
