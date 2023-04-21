from __future__ import annotations

from typing import Literal, TYPE_CHECKING
from datetime import time
import random

import discord
from discord import app_commands, Interaction
from discord.ext import commands, tasks

from modules import EmbedGen, Paginators, Graphs
from ._utils import Wealth, get_wealth

if TYPE_CHECKING:
    from WorstBot import WorstBot


class Economy(commands.GroupCog, name = "economy"):
    CONVERSION_MAX = 0.5
    CONVERSION_MIN = 0.05
    CONVERSION_WEIGHTS = {
        "crash": 0.005,
        "decrease": 0.5,
        "increase": 0.5,
        "boom": 0.005
    }
    conversion_rate: float = 0.25

    transfer_group = app_commands.Group(name = "transfer", description = "Transfer money")
    gambling_group = app_commands.Group(name = "gamble", description = "Gamble money")

    def __init__(self, bot: WorstBot):
        self.bot = bot
        self.bot.economy: dict[discord.Object, Wealth] = {}

    async def cog_load(self) -> None:
        if not await self.bot.execute("SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'recipient_type')"):
            await self.bot.execute(f"CREATE TYPE recipient_type as ENUM('global', 'guild', 'user', 'worstbot', 'bank', 'wallet')")
        await self.bot.execute("CREATE TABLE IF NOT EXISTS economy(user_id BIGINT, guild_id BIGINT, wallet FLOAT DEFAULT 0.0, bank FLOAT DEFAULT 0.0, tokens FLOAT DEFAULT 0.0, multiplier FLOAT DEFAULT 1.0, PRIMARY KEY (user_id, guild_id))")
        await self.bot.execute("CREATE TABLE IF NOT EXISTS transactions(user_id BIGINT, recipient recipient_type, recipient_id BIGINT DEFAULT 0, amount FLOAT, timestamp timestamptz)")

        self.conversion_rate = await self.bot.fetchval("SELECT amount FROM transactions WHERE recipient = 'worstbot' ORDER BY timestamp DESC LIMIT 1") or self.conversion_rate

        self.bot.logger.debug(f"Conversion rate: {self.conversion_rate}")
        self.load_economy.start()
        self.create_conversion_rate.start()
        await self.create_conversion_rate()
        self.bot.logger.info("Economy.Economy cog loaded")

    async def cog_unload(self) -> None:
        self.create_conversion_rate.cancel()
        self.bot.logger.info("Economy.Economy cog unloaded")

    @tasks.loop(count = 1)
    async def load_economy(self):
        self.bot.logger.debug("Loading economy data")
        economy = await self.bot.fetch("SELECT user_id, guild_id, wallet, bank, tokens, multiplier FROM economy")
        for user_id, guild_id, wallet, bank, tokens, multiplier in economy:
            self.bot.logger.debug(f"{user_id} {guild_id} {wallet} {bank} {tokens} {multiplier}")
            self.bot.economy[discord.Object(user_id, type = discord.Member)] = Wealth(member_id = user_id, guild_id = guild_id, wallet = wallet, bank = bank, tokens = tokens, multiplier = multiplier)

    @tasks.loop(time = time(1, 0))
    async def create_conversion_rate(self):
        conversion_rate = random.choices(list(self.CONVERSION_WEIGHTS.keys()), list(self.CONVERSION_WEIGHTS.values()))[0]

        if conversion_rate == "crash":
            self.conversion_rate = self.CONVERSION_MIN
        elif conversion_rate == "boom":
            self.conversion_rate = self.CONVERSION_MAX
        elif conversion_rate == "increase":
            self.conversion_rate = min(self.conversion_rate + random.uniform(0.01, 0.05), self.CONVERSION_MAX)
        else:
            self.conversion_rate = max(self.conversion_rate - random.uniform(0.01, 0.05), self.CONVERSION_MIN)
        await self.bot.execute("INSERT INTO transactions(recipient, amount, timestamp) VALUES('worstbot', $1, now()::timestamptz)", self.conversion_rate)
        self.bot.logger.debug(f"Conversion rate changed to {self.conversion_rate * 100:.2f}%")

    @load_economy.before_loop
    @create_conversion_rate.before_loop
    async def before_ready(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name = "leaderboard")
    async def leaderboard(self, interaction: Interaction):
        """Check how you stack up against your friends on the leaderboard

        :param interaction:
        :return:
        """
        economy = await self.bot.fetch("SELECT user_id, wallet+bank as wealth FROM economy WHERE guild_id = $1 ORDER BY wealth DESC LIMIT 500", interaction.guild_id)
        economy_str = "\n".join([f"{i + 1}) {await self.bot.maybe_fetch_user(user_id)}: W${wealth:,}" for i, (user_id, wealth) in enumerate(economy)])
        embeds = EmbedGen.SimpleEmbedList(
            title = "Economy Leaderboard",
            descriptions = economy_str
        )
        view = Paginators.ButtonPaginatedEmbeds(embed_list = embeds)
        await interaction.response.send_message(view = view, embeds = embeds, ephemeral = True)
        view.response = await interaction.original_response()

    @app_commands.command(name = "stats")
    async def stats(self, interaction: Interaction, graph_type: Literal["pie", "bar", "line"]):    # todo: Graph based stats
        """Check how you stack up against your friends, graph edition

        :param interaction:
        :param graph_type: Visual representation of the data
        :return:
        """

    @transfer_group.command(name = "ascend")
    async def to_tokens(self, interaction: Interaction, amount: float):
        """Ascend your money to tokens

        :param interaction:
        :param amount: The amount of money to convert
        :return:
        """
        await interaction.response.defer(ephemeral = True)
        user = await get_wealth(self.bot, interaction.guild, interaction.user)
        amount = min(amount, user.wallet)

        await user.to_tokens(self.bot, amount, self.conversion_rate)
        await self.bot.execute("INSERT INTO transactions(user_id, recipient, recipient_id, amount, timestamp) VALUES($1, 'global', 0, $2, now()::timestamptz)", interaction.user.id, amount * self.conversion_rate)

        await interaction.followup.send(f"Successfully converted W${amount:,.2f} to {amount * self.conversion_rate:,.2f} tokens", ephemeral = True)
        self.bot.logger.debug(f"{interaction.user.id} converted W${amount:,.2f} to {amount * self.conversion_rate:,.2f} tokens")

    @transfer_group.command(name = "give")
    async def to_user(self, interaction: Interaction, amount: float, user: discord.Member):
        """Gift money to another user

        :param interaction:
        :param amount: The amount to give
        :param user: The user to give it to
        :return:
        """
        owner = await get_wealth(self.bot, interaction.guild, interaction.user)
        recipient = await get_wealth(self.bot, interaction.guild, user)
        amount = min(amount, owner.wallet)

        await owner.to_user(self.bot, amount, recipient)
        await self.bot.execute("INSERT INTO transactions(user_id, recipient, recipient_id, amount, timestamp) VALUES($1, 'user', $2, $3, now()::timestamptz)", interaction.user.id, user.id, amount)

        await interaction.response.send_message(f"Successfully gifted W${amount:,.2f} to {user.mention}", ephemeral = True)
        self.bot.logger.debug(f"{interaction.user.id} gifted W${amount:,.2f} to {user.id}")

    @transfer_group.command(name = "deposit")
    async def to_bank(self, interaction: Interaction, amount: float):
        """Deposit money into your bank account

        :param interaction:
        :param amount: The amount to deposit
        :return:
        """
        user = await get_wealth(self.bot, interaction.guild, interaction.user)
        amount = min(amount, user.wallet)

        await user.to_bank(self.bot, amount)
        await self.bot.execute("INSERT INTO transactions(user_id, recipient, recipient_id, amount, timestamp) VALUES($1, 'bank', 0, $2, now()::timestamptz)", interaction.user.id, amount)

        await interaction.response.send_message(f"Successfully deposited W${amount:,.2f} into your bank account", ephemeral = True)
        self.bot.logger.debug(f"{interaction.user.id} deposited W${amount:,.2f} into their bank account")

    @transfer_group.command(name = "withdraw")
    async def to_wallet(self, interaction: Interaction, amount: float):
        """Withdraw money from your bank account

        :param interaction:
        :param amount: The amount to withdraw
        :return:
        """
        user = await get_wealth(self.bot, interaction.guild, interaction.user)
        amount = min(amount, user.bank)

        await user.to_wallet(self.bot, amount)
        await self.bot.execute("INSERT INTO transactions(user_id, recipient, recipient_id, amount, timestamp) VALUES($1, 'wallet', 0, $2, now()::timestamptz)", interaction.user.id, amount)

        await interaction.response.send_message(f"Successfully withdrew W${amount:,.2f} from your bank account", ephemeral = True)
        self.bot.logger.debug(f"{interaction.user.id} withdrew W${amount:,.2f} from their bank account")

    @app_commands.command(name = "balance")
    async def view_wealth(self, interaction: Interaction):
        """View your current wealth

        :param interaction:
        :return:
        """
        user = await get_wealth(self.bot, interaction.guild, interaction.user)
        embed = EmbedGen.FullEmbed(
            title = f"{interaction.user.name}'s Wealth",
            fields = [
                EmbedGen.EmbedField(name = name, value = value) for name, value in zip(
                    ["Wallet", "Bank", "Tokens", "\u200b", "Multiplier", "\u200b"],
                    [f"W${user.wallet:,.2f}", f"W${user.bank:,.2f}", f"{user.tokens:,.2f}", "\u200b", f"{user.multiplier * 100:.0f}%", "\u200b"],
                    strict = True
                )
            ],
            footer = {"text": f"Conversion rate: {self.conversion_rate * 100:.2f}%"}
        )
        await interaction.response.send_message(embed = embed, ephemeral = True)


async def setup(bot):
    await bot.add_cog(Economy(bot))