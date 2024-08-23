from __future__ import annotations

import random
from datetime import time, timezone
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.app_commands import Range
from discord.ext import commands, tasks

from ....core.utils import paginators
from .. import (
    BASE_RATE,
    CONVERSION_MAX,
    CONVERSION_MIN,
    CONVERSION_WEIGHTS,
    LEADERBOARD_SIZE,
    PAGE_SIZE,
    Transactions,
    Wealth,
    ascend,
    deposit,
    get_wealth,
    transfer,
    withdraw,
)
from . import embeds

if TYPE_CHECKING:
    from discord import Embed, Interaction, Member

    from WorstBot import Bot

with open("WorstBot/extensions/economy/base/leaderboard.sql", "r") as f:
    leaderboard_sql = f.read()


@app_commands.default_permissions()
@app_commands.guild_only()
class Economy(commands.GroupCog, name="economy"):

    def __init__(self, bot: Bot):
        self.bot = bot
        self.logger = self.bot.log_handler.getChild(self.qualified_name)

    async def cog_load(self) -> None:
        self.logger.info(f"{self.qualified_name} cog loaded")

        self.conversion_rate = await self.fetch_conversion_rate() or BASE_RATE
        self.update_conversion_rate.start()

        self.get_wealth = await get_wealth(self.bot)

    async def cog_unload(self) -> None:
        self.logger.info(f"{self.qualified_name} cog unloaded")

    async def fetch_conversion_rate(self) -> float:
        return await self.bot.pool.fetchval(
            "SELECT amount::float FROM economy WHERE transaction = $1 AND member is NUlL ORDER BY transaction_timestamp DESC LIMIT 1",
            Transactions.conversion_rate,
        )

    async def set_conversion_rate(self, rate: float) -> None:
        self.conversion_rate = rate
        await self.bot.pool.execute(
            "INSERT INTO economy(transaction, amount) VALUES($1, $2)", Transactions.conversion_rate, rate
        )

    @tasks.loop(time=time(1, 0, tzinfo=timezone.utc))
    async def update_conversion_rate(self):
        choice = random.choices(list(CONVERSION_WEIGHTS.keys()), list(CONVERSION_WEIGHTS.values()))[0]
        match choice:
            case "crash":
                rate = CONVERSION_MIN
            case "decrease":
                rate = max(self.conversion_rate - random.uniform(0.01, 0.05), CONVERSION_MIN)
            case "increase":
                rate = min(self.conversion_rate + random.uniform(0.01, 0.05), CONVERSION_MAX)
            case "boom":
                rate = CONVERSION_MAX

        await self.set_conversion_rate(rate)
        self.logger.debug(f"Conversion rate updated to {self.conversion_rate:.2%}")

    @update_conversion_rate.before_loop
    async def before_read(self):
        await self.bot.wait_until_ready()

    async def prepare_leaderboard(self, user: Member) -> list[list[Wealth]]:
        data = await self.bot.pool.fetch(leaderboard_sql, user.guild.id, user.id, LEADERBOARD_SIZE)
        if not data:
            return []

        leaderboard = []
        guild = user.guild
        for row in data:
            member = guild.get_member(row["user_id"])
            if not member:
                continue

            leaderboard.append(Wealth(member, row["combined_balance"]))

        return [page for page in paginators.prepare_pages(leaderboard, PAGE_SIZE)]

    @app_commands.command(name="leaderboard")
    async def leaderboard(self, interaction: Interaction) -> None:
        """Compare wealth with other members in the server

        Args:
            interaction (Interaction): _description_
        """
        assert isinstance(interaction.user, discord.Member)
        leaderboard = await self.prepare_leaderboard(interaction.user)

        items: list[Embed] = [embeds.Leaderboard(wealths, i * PAGE_SIZE) for i, wealths in enumerate(leaderboard)]
        view = paginators.ButtonPaginatedEmbeds(items)
        await interaction.followup.send(view=view, embed=items[0], ephemeral=True)
        view.response = await interaction.original_response()

    @app_commands.command(name="ascend")
    async def to_tokens(self, interaction: Interaction, amount: Range[float, 0.0]) -> None:
        """Ascend wallet balance to tokens

        Args:
            interaction (Interaction): _description_
            amount (Range[float, 0.0]): The amount of W$ to ascend
        """
        assert isinstance(interaction.user, discord.Member)
        wealth = await self.get_wealth(interaction.user)

        amount = min(amount, wealth.wallet)

        wealth = await ascend(self.bot, wealth, amount, self.conversion_rate)
        embed = embeds.Balance(wealth)
        content = f"Successfully ascended W${amount} to {amount * self.conversion_rate} tokens"
        await interaction.followup.send(embed=embed, content=content, ephemeral=True)

    @app_commands.command(name="give")
    async def to_other(self, interaction: Interaction, amount: Range[float, 0.0], recipient: discord.Member) -> None:
        """Gift W$ to another member

        Args:
            interaction (Interaction): _description_
            amount (Range[float, 0.0]): The amount to send
            recipient (discord.Member): The person to send to
        """
        assert isinstance(interaction.user, discord.Member)
        wealth = await self.get_wealth(interaction.user)
        recipient_wealth = await self.get_wealth(recipient)

        amount = min(amount, wealth.wallet)

        wealth, _ = await transfer(self.bot, wealth, recipient_wealth, amount)
        embed = embeds.Balance(wealth)
        content = f"Successfully transferred W${amount} to {recipient.mention}"
        await interaction.followup.send(embed=embed, content=content, ephemeral=True)

    @app_commands.command(name="deposit")
    async def to_bank(self, interaction: Interaction, amount: Range[float, 0.0]) -> None:
        """Deposit W$ to bank

        Args:
            interaction (Interaction): _description_
            amount (Range[float, 0.0]): The amount to deposit
        """
        assert isinstance(interaction.user, discord.Member)
        wealth = await self.get_wealth(interaction.user)

        amount = min(amount, wealth.wallet)

        await deposit(self.bot, wealth, amount)
        await interaction.followup.send(embed=embeds.Balance(wealth), ephemeral=True)

    @app_commands.command(name="withdraw")
    async def to_wallet(self, interaction: Interaction, amount: Range[float, 0.0]) -> None:
        """Withdraw W$ from bank

        Args:
            interaction (Interaction): _description_
            amount (Range[float, 0.0]): The amount to withdraw
        """
        assert isinstance(interaction.user, discord.Member)
        wealth = await self.get_wealth(interaction.user)

        amount = min(amount, wealth.bank)

        await withdraw(self.bot, wealth, amount)
        await interaction.followup.send(embed=embeds.Balance(wealth), ephemeral=True)

    @app_commands.command(name="balance")
    async def balance(self, interaction: Interaction) -> None:
        """View your current wealth

        Args:
            interaction (Interaction): _description_
        """
        assert isinstance(interaction.user, discord.Member)
        wealth = await self.get_wealth(interaction.user)
        await interaction.followup.send(embed=embeds.Balance(wealth), ephemeral=True)


async def setup(bot: Bot) -> None:
    await bot.add_cog(Economy(bot))
