from __future__ import annotations

from typing import Literal, TYPE_CHECKING, Self
from dataclasses import dataclass
from datetime import time
import random

import discord
from discord import app_commands, Interaction
from discord.ext import commands, tasks

from modules import EmbedGen, Paginators, Graphs

if TYPE_CHECKING:
    from WorstBot import WorstBot

@dataclass
class Wealth:
    member_id: int
    guild_id: int
    wallet: float = 0.0
    bank: float = 0.0
    tokens: float = 0.0
    multiplier: float = 1.0

    async def sync(self, bot: WorstBot) -> None:
        bot.logger.debug(f"Syncing {self.member_id} {self.guild_id} {self.wallet} {self.bank} {self.tokens} {self.multiplier}")
        await bot.execute("INSERT INTO economy(user_id, guild_id, wallet, bank, tokens, multiplier) VALUES ($1, $2, $3, $4, $5, $6) ON CONFLICT (user_id, guild_id) DO UPDATE SET wallet=excluded.wallet, bank=excluded.bank, tokens=excluded.tokens, multiplier=excluded.multiplier", self.member_id, self.guild_id, self.wallet, self.bank, self.tokens, self.multiplier)

    async def to_bank(self, bot: WorstBot, amount: float) -> Self:
        self.wallet -= amount
        self.bank += amount
        await self.sync(bot)
        return self

    async def to_wallet(self, bot: WorstBot, amount: float) -> Self:
        self.wallet += amount
        self.bank -= amount
        await self.sync(bot)
        return self

    async def to_tokens(self, bot: WorstBot, amount: float, conversion_rate: float) -> Self:
        self.wallet -= amount
        self.tokens += amount * conversion_rate
        await self.sync(bot)
        return self

    async def to_user(self, bot: WorstBot, amount: float, user: Wealth) -> (Self, Wealth):
        self.wallet -= amount
        user.wallet += amount

        await self.sync(bot)
        await user.sync(bot)

        return self, user
class Economy(commands.GroupCog, name = "economy"):
    CONVERSION_MAX = 0.5
    CONVERSION_MIN = 0.05
    CONVERSION_WEIGHTS = {
        "crash": 0.005,
        "decrease": 0.5,
        "increase": 0.5,
        "boom": 0.005
    }
    conversion_rate: float = 1.0

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
        self.bot.logger.info("Economy.Economy cog loaded")

    async def cog_unload(self) -> None:
        self.create_conversion_rate.cancel()
        self.bot.logger.info("Economy.Economy cog unloaded")

    async def get_wealth(self, guild: discord.Guild, user: discord.Member) -> Wealth:
        wealth: Wealth
        if wealth := self.bot.economy.get(user):
            self.bot.logger.debug(f"{wealth.member_id} cache hit", )
            return wealth

        row = await self.bot.fetchrow("SELECT user_id, guild_id, wallet, bank, tokens, multiplier FROM economy WHERE user_id = $1 AND guild_id = $2", user.id, guild.id)
        if not row:
            await self.bot.execute("INSERT INTO economy(user_id, guild_id) VALUES ($1, $2) ON CONFLICT DO NOTHING", user.id, guild.id)
            wealth = Wealth(user.id, guild.id)
            self.bot.logger.debug(f"New user: {wealth.member_id}", )
        else:
            wealth = Wealth(*row)
            self.bot.logger.debug(f"{wealth.member_id} cache miss", )
        self.bot.economy[user] = wealth

        return wealth

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
        economy_str = "\n".join([f"{i + 1}) {await self.bot.maybe_fetch_user(user_id)}: {wealth:,}" for
                                 i, (user_id, wealth) in enumerate(economy)])
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
        user = await self.get_wealth(interaction.guild, interaction.user)
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
        owner = await self.get_wealth(interaction.guild, interaction.user)
        recipient = await self.get_wealth(interaction.guild, user)
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
        user = await self.get_wealth(interaction.guild, interaction.user)
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
        user = await self.get_wealth(interaction.guild, interaction.user)
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
        user = await self.get_wealth(interaction.guild, interaction.user)
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

    @app_commands.command(name = "spawn_money")
    @app_commands.checks.cooldown(1, 60, key = lambda i: (i.guild_id, i.user.id))
    async def spawn_money(self, interaction: Interaction):
        """Spawn some money for yourself

        :param interaction:
        :return:
        """
        user = await self.get_wealth(interaction.guild, interaction.user)
        amount = random.randint(100, 1000)

        user.wallet += amount
        await user.sync(self.bot)
        await self.bot.execute("INSERT INTO transactions(user_id, recipient, recipient_id, amount, timestamp) VALUES($1, 'wallet', -1, $2, now()::timestamptz)", interaction.user.id, amount)

        await interaction.response.send_message(f"Successfully spawned W${amount:,.2f} into your wallet", ephemeral = True)
        self.bot.logger.debug(f"{interaction.user.id} spawned W${amount:,.2f} into their wallet")


async def setup(bot):
    await bot.add_cog(Economy(bot))
