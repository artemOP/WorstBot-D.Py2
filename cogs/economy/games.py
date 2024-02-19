from __future__ import annotations

from asyncio import sleep
from collections import deque
from enum import Enum
from random import choices, randint
from typing import TYPE_CHECKING

import discord
from discord import app_commands, Interaction, ui
from discord.ext import commands

from ._utils import get_wealth
from modules import EmbedGen, Paginators, Converters

if TYPE_CHECKING:
    from discord import Emoji, Guild
    from WorstBot import WorstBot
    from ._utils import Wealth
    from typing import Optional


class Games(Enum):
    blackjack = "Blackjack"
    roulette = "Roulette"


class GameState(Enum):
    cancelled = -1
    waiting = 0
    playing = 1
    finished = 2


class PlayerState(Enum):
    unready = 0
    ready = 1
    playing = 2
    sticking = 3
    bust = 4


class Cards(Enum):
    ace = 11
    two = 2
    three = 3
    four = 4
    five = 5
    six = 6
    seven = 7
    eight = 8
    nine = 9
    ten = 10
    jack = 10
    queen = 10
    king = 10


class RouletteBets(Enum):
    red = "red 1:1"
    black = "black 1:1"
    odd = "odd 1:1"
    even = "even 1:1"
    low = "low 1:1 (1-18)"
    high = "high 1:1 (19-36)"
    column_1 = f"column 1 2:1 ({', '.join(str(i) for i in range(1, 37, 3))})"
    column_2 = f"column 2 2:1 ({', '.join(str(i) for i in range(2, 37, 3))})"
    column_3 = f"column 3 2:1 ({', '.join(str(i) for i in range(3, 37, 3))})"
    dozen_1 = "1st dozen 2:1 (1-12)"
    dozen_2 = "2nd dozen 2:1 (13-24)"
    dozen_3 = "3rd dozen 2:1 (25-36)"
    lower_straight_up = "straight up 35:1 (0-18)"
    upper_straight_up = "straight up 35:1 (19-36)"
    street = "street 11:1"
    basket = "basket 6:1"


class RouletteColours(Enum):
    green = {0}
    red = {3, 9, 12, 18, 21, 27, 30, 36, 5, 14, 23, 32, 1, 7, 16, 19, 25, 28, 34}
    black = {2, 4, 6, 8, 10, 11, 13, 15, 17, 19, 20, 22, 24, 26, 29, 31, 33, 35}


class Player:
    def __init__(self, wealth: Wealth, bet: int, state: PlayerState = PlayerState.unready):
        self.wealth: Wealth = wealth
        self.bet: int = bet
        self.state: PlayerState = state
        self.view: Optional[Lobby | Game] = None


def blackjack_embed(game: GameManager, cards: list[Emoji]) -> EmbedGen.FullEmbed:
    score = 0

    for card in cards:
        name = card.name.split("_")[1]
        score += Cards[name].value

        if name == "ace" and score > 21:
            score -= 10

    return EmbedGen.FullEmbed(title = "Blackjack",
                              fields = [
                                  EmbedGen.EmbedField(name = "Your Hand", value = "".join(f"<:{card.name}:{card.id}>" for card in cards)),
                                  EmbedGen.EmbedField(name = "Your Score", value = f"{score}"),
                                  EmbedGen.EmbedField(name = "Dealer's Hand", value = f"{game.dealer[0]}{game.card_back}")
                              ],
                              extras = {"score": score}
                              )


class GameManager:
    def __init__(self, mode: Games, bot: WorstBot, owner: Player):
        self.mode: Games = mode
        self.bot: WorstBot = bot
        self.state: GameState = GameState.waiting
        self.players: list[Player] = [owner]

    async def add_player(self, wealth: Wealth, bet: int) -> Player:
        player = Player(wealth, bet)
        self.players.append(player)
        await self.update_player_count()
        return player

    async def remove_player(self, wealth: Wealth) -> None:
        for player in self.players:
            if player.wealth is not wealth:
                continue

            self.players.remove(player)
            break

        await self.update_player_count()
        return

    async def update_player_count(self) -> None:
        player_count = str(len(self.players))
        for player in self.players:
            if not player.view:
                continue
            embed = player.view.response.embeds[0].to_dict()
            embed["fields"][0]["value"] = player_count
            await player.view.response.edit(embed = discord.Embed.from_dict(embed))

    async def start(self, interaction: Interaction):
        self.state = GameState.playing

        match self.mode:
            case Games.blackjack:
                self.cards: deque[Emoji] = deque(choices([emoji for emoji in self.bot.custom_emoji if emoji.name.startswith("card_")], k = 52))
                card_back: list = [emoji for emoji in self.bot.custom_emoji if emoji.name == "back_card"]
                self.card_back: Emoji | str = "\U00002753" if not card_back else card_back[0]

                self.dealer: list[Emoji] = [self.cards.pop(), self.cards.pop()]

                for player in self.players:
                    cards = [self.cards.pop(), self.cards.pop()]

                    view = Blackjack(self, player, cards)
                    embed = blackjack_embed(self, cards)

                    response = await player.view.response.edit(embed = embed, view = view)
                    view.response = response

                    player.view = view
                    player.state = PlayerState.playing

            case Games.roulette:
                number = randint(0, 36)
                colour = next(colour for colour in RouletteColours if number in colour.value)
                for player in self.players:
                    view = Roulette(self, player, (number, colour))
                    player_embed = EmbedGen.FullEmbed(
                        title = "Roulette",
                        image = "https://cdnl.iconscout.com/lottie/premium/thumb/roulette-wheel-5290230-4464271.gif"
                    )

                    response = await player.view.response.edit(embed = player_embed, view = view)
                    view.response = response

                    player.view = view
                    player.state = PlayerState.playing

            case _:
                raise NotImplementedError(f"Game {self.mode.name} not implemented")

    async def cancel(self, interaction: Interaction):
        self.state = GameState.cancelled
        for player in self.players:
            await player.view.response.edit(view = None, embed = None, content = "The game has been cancelled by the host", delete_after = 30)
        await interaction.response.send_message("The game has been cancelled", ephemeral = True)


class Lobby(Paginators.BaseView):
    def __init__(self, game: GameManager, player: Player):
        super().__init__(timeout = 10 * 60)
        self.game: GameManager = game
        self.player: Player = player


class HostLobby(Lobby):
    def __init__(self, game: GameManager, player: Player):
        super().__init__(game, player)

    @ui.button(label = "Start", style = discord.ButtonStyle.green)
    async def start(self, interaction: Interaction, button: ui.Button):
        if all(player.state is PlayerState.ready for player in self.game.players):
            await interaction.response.defer()
            await self.game.start(interaction)
            self.stop()
        else:
            await interaction.response.send_message("Not all players are ready", ephemeral = True)

    @ui.button(label = "Cancel", style = discord.ButtonStyle.red)
    async def cancel(self, interaction: Interaction, button: ui.Button):
        await self.game.cancel(interaction)
        self.stop()


class GuestLobby(Lobby):
    def __init__(self, game: GameManager, player: Player):
        super().__init__(game, player)

    @ui.button(label = "ready", style = discord.ButtonStyle.green)
    async def ready(self, interaction: Interaction, button: ui.Button):
        self.player.state = PlayerState.ready
        button.disabled = True
        await interaction.response.edit_message(view = self)

    @ui.button(label = "exit", style = discord.ButtonStyle.red)
    async def exit(self, interaction: Interaction, button: ui.Button):
        await self.game.remove_player(await get_wealth(interaction.client, interaction.guild, interaction.user))
        await interaction.response.edit_message(view = None, embed = None, content = "You have left the lobby")
        self.stop()


class Game(Paginators.BaseView):
    def __init__(self, game: GameManager, player: Player):
        super().__init__(timeout = 10 * 60)
        self.game: GameManager = game
        self.player: Player = player

    async def on_timeout(self) -> None:
        self.game.state = GameState.cancelled
        for player in self.game.players:
            await player.view.response.edit(view = None, embed = None, content = "The game has been cancelled due to inactivity")
            player.view.stop()

class Blackjack(Game):
    def __init__(self, game: GameManager, player: Player, cards: list[Emoji]):
        super().__init__(game, player)
        self.cards: list[Emoji] = cards
        self.score = sum(Cards[card.name.split("_")[1]].value for card in cards)

    @ui.button(label = "Hit", style = discord.ButtonStyle.green)
    async def hit(self, interaction: Interaction, button: ui.Button):
        self.cards.append(self.game.cards.pop())
        embed = blackjack_embed(self.game, self.cards)
        self.score = embed.extras.get("score")

        if self.score <= 21:
            return await interaction.response.edit_message(embed = embed)

        for children in self.children:
            children.disabled = True
        await self.player.wealth.punish(interaction.client, self.player.bet)
        self.player.state = PlayerState.bust

        await interaction.response.edit_message(view = self, embed = embed, content = "You have gone bust")
        if not any(player.state is PlayerState.playing for player in self.game.players):
            await self.game_end(interaction)

    @ui.button(label = "Stand", style = discord.ButtonStyle.gray)
    async def stand(self, interaction: Interaction, button: ui.Button):
        for children in self.children:
            children.disabled = True

        self.player.state = PlayerState.sticking
        if any(player.state is PlayerState.playing for player in self.game.players):
            return await interaction.response.edit_message(view = self, content = "Waiting for other players")

        await self.game_end(interaction)

    @ui.button(label = "Double Down", style = discord.ButtonStyle.red)
    async def double_down(self, interaction: Interaction, button: ui.Button):
        if self.player.wealth.wallet < self.player.bet:
            return await interaction.response.send_message("You don't have enough money to double down", ephemeral = True)
        self.player.bet *= 2

        self.player.state = PlayerState.sticking
        await self.hit.callback(interaction)
        for children in self.children:
            children.disabled = True
        await self.response.edit(view = self, content = "Waiting for other players")

        if not any(player.state is PlayerState.playing for player in self.game.players):
            await self.game_end(interaction)

    @ui.button(label = "Fold", style = discord.ButtonStyle.red)
    async def fold(self, interaction: Interaction, button: ui.Button):
        self.player.state = PlayerState.bust
        await interaction.response.edit_message(view = None, embed = None, content = "You have folded")
        if not any(player.state is PlayerState.playing for player in self.game.players):
            await self.game_end(interaction)

    async def game_end(self, interaction: Interaction):
        self.game.state = GameState.finished
        if sum(Cards[card.name.split("_")[1]].value for card in self.game.dealer) < 17:
            self.game.dealer.append(self.game.cards.pop())
        dealer_score = sum(Cards[card.name.split("_")[1]].value for card in self.game.dealer)
        if dealer_score > 21:
            dealer_score = 0
        winners = [player for player in self.game.players if player.state is PlayerState.sticking and sum(Cards[card.name.split("_")[1]].value for card in player.view.cards) > dealer_score]
        winners = sorted(winners, key = lambda player: (-player.view.score, len(player.view.cards)))
        winner = winners[0] if winners else None

        embed = EmbedGen.FullEmbed(title = "Blackjack",
                                   fields = [EmbedGen.EmbedField(name = "Winner", value = interaction.guild.get_member(winner.wealth.member_id).mention if winner else "Dealer wins"),
                                             EmbedGen.EmbedField(name = "Winning Hand", value = "".join(str(card) for card in winner.view.cards) if winner else "".join(str(card) for card in self.game.dealer)),
                                             EmbedGen.EmbedField(name = "Payout", value = f"W${winner.bet * 2 if winner else '0'}")
                                             ]
                                   )
        for player in self.game.players:
            await player.wealth.punish(interaction.client, player.bet)
            await player.view.response.edit(embed = embed, view = None, content = None)
            player.view.stop()
        if winner:
            await winners[0].wealth.reward(interaction.client, winners[0].bet * 2)


class Roulette(Game):
    def __init__(self, game: GameManager, player: Player, winning_number: tuple[int, RouletteColours]):
        super().__init__(game, player)
        self.winning_number: tuple[int, RouletteColours] = winning_number
        self.bet_type.options = [discord.SelectOption(label = item.value, value = item.name) for item in RouletteBets]
        self.bet: list[int | RouletteBets] = []

    @ui.select(placeholder = "Select a bet type")
    async def bet_type(self, interaction: Interaction, select: ui.Select):
        bet_type = RouletteBets[select.values[0]]
        match bet_type:
            case None:
                return await interaction.response.send_message("Please place a bet", ephemeral = True)
            case RouletteBets.lower_straight_up:
                self.bet_value.options = [discord.SelectOption(label = str(number), value = str(number)) for number in range(0, 19)]
                self.bet_value.disabled = False

            case RouletteBets.upper_straight_up:
                self.bet_value.options = [discord.SelectOption(label = str(number), value = str(number)) for number in range(19, 37)]
                self.bet_value.disabled = False

            case RouletteBets.street:
                self.bet_value.options = [discord.SelectOption(label = f"{number} - {number + 2}", value = f"{number}-{number + 2}") for number in range(1, 37, 3)]
                self.bet_value.disabled = False

            case _:
                self.bet_value.options = []
                self.bet_value.disabled = False
                self.bet = [bet_type]
                self.confirm.disabled = False

        self.bet_type.disabled = True
        self.bet_value.options.append(discord.SelectOption(label = "Back", value = "Back"))
        await interaction.response.edit_message(view = self)

    @ui.select(placeholder = "Select a bet", disabled = True, options = [discord.SelectOption(label = "1", value = "1")])
    async def bet_value(self, interaction: Interaction, select: ui.Select):
        bet = select.values[0].split("-")
        if bet == ["Back"]:
            self.bet_type.disabled = False
            self.bet_value.disabled = True
            return await interaction.response.edit_message(view = self)
        elif len(bet) == 2:
            self.bet = [_ for _ in range(int(bet[0]), int(bet[1]) + 1)]
        else:
            self.bet = [int(bet[0])]

        self.confirm.disabled = False
        await interaction.response.edit_message(view = self)

    @ui.button(label = "Confirm", style = discord.ButtonStyle.green, disabled = True)
    async def confirm(self, interaction: Interaction, button: ui.Button):
        if not self.bet:
            return await interaction.response.send_message("Please place a bet", ephemeral = True)
        self.player.state = PlayerState.sticking

        if all(player.state is PlayerState.sticking for player in self.game.players):
            await interaction.response.edit_message(view = None, content = None)
            await self.game_end(interaction)
        else:
            await interaction.response.edit_message(view = None, content = "You have placed your bet, please wait for other players")

    async def game_end(self, interaction: Interaction):
        winners: list[discord.Member] = []

        async def reward_winner(player: Player, multiplier: int):
            winners.append(interaction.guild.get_member(player.wealth.member_id))
            await player.wealth.reward(interaction.client, player.bet * multiplier)

        for player in self.game.players:
            await player.wealth.punish(interaction.client, player.bet)
            bet = player.view.bet

            if len(bet) == 1 and isinstance(bet[0], int):  # Straight up
                if self.winning_number[0] == bet[0]:
                    await reward_winner(player, 36)
            elif (
                    (bet[0] is RouletteBets.red and self.winning_number[1] is RouletteColours.red) or  # Red
                    (bet[0] is RouletteBets.black and self.winning_number[1] is RouletteColours.black) or  # Black
                    (bet[0] is RouletteBets.even and self.winning_number[0] % 2 == 0) or  # Even
                    (bet[0] is RouletteBets.odd and self.winning_number[0] % 2 == 1) or  # Odd
                    (bet[0] is RouletteBets.low and 1 <= self.winning_number[0] <= 18) or  # Low
                    (bet[0] is RouletteBets.high and 19 <= self.winning_number[0] <= 36)  # High
            ):
                await reward_winner(player, 2)
            elif (
                    (bet[0] is RouletteBets.column_1 and self.winning_number[0] in range(1, 37, 3)) or  # Column 1
                    (bet[0] is RouletteBets.column_2 and self.winning_number[0] in range(2, 37, 3)) or  # Column 2
                    (bet[0] is RouletteBets.column_3 and self.winning_number[0] in range(3, 37, 3)) or  # Column 3
                    (bet[0] is RouletteBets.dozen_1 and 1 <= self.winning_number[0] <= 12) or  # Dozen 1
                    (bet[0] is RouletteBets.dozen_2 and 13 <= self.winning_number[0] <= 24) or  # Dozen 2
                    (bet[0] is RouletteBets.dozen_3 and 25 <= self.winning_number[0] <= 36)  # Dozen 3
            ):
                await reward_winner(player, 3)
            elif len(bet) == 3 and self.winning_number[0] in bet:  # Street
                await reward_winner(player, 12)
            elif bet[0] is RouletteBets.basket and 0 <= self.winning_number[0] <= 3:  # Basket
                await reward_winner(player, 6)

        embed = EmbedGen.FullEmbed(
            title = "Winners",
            description = "\n".join([f"{member.mention}" for member in winners]) or "No winners",
            fields = [EmbedGen.EmbedField(name = "Winning combination: ", value = f"{self.winning_number[1].name} {self.winning_number[0]}")],
        )
        for player in self.game.players:
            await player.view.response.edit(embed = embed, view = None, content = None)
            player.view.stop()

        self.game.state = GameState.finished


class Gambling(commands.GroupCog, name = "gambling"):

    def __init__(self, bot: WorstBot):
        self.bot = bot
        self.logger = self.bot.logger.getChild(self.qualified_name)
        self.games: dict[Guild, dict[Games: GameManager]] = {}

    async def cog_load(self) -> None:
        self.logger.info(f"{self.qualified_name} cog loaded")

    async def cog_unload(self) -> None:
        self.logger.info(f"{self.qualified_name} cog unloaded")

    @app_commands.command(name = "start")
    async def start_lobby(self, interaction: Interaction, game: Games, bet: app_commands.Range[int, 100, 100_000]):
        """Start a gambling lobby using WorstCoin

        :param interaction:
        :param game: Type of game to play
        :param bet: Amount of WorstCoin to bet: 100-100,000
        :return:
        """
        wealth = await get_wealth(self.bot, interaction.guild, interaction.user)
        if interaction.guild not in self.games:
            self.games[interaction.guild] = {}

        if game in self.games[interaction.guild] and self.games[interaction.guild][game].state not in (GameState.cancelled, GameState.finished):
            return await interaction.response.send_message(f"{game.name.title()} lobby already open, join it with {Converters.to_command_mention(self.join_lobby, interaction.guild)}", ephemeral = True)
        elif wealth.wallet < bet:
            return await interaction.response.send_message(f"You need at least {bet} WorstCoin in your wallet to start a lobby with this bet", ephemeral = True)

        player = Player(wealth, bet, PlayerState.ready)
        self.games[interaction.guild][game] = game = GameManager(game, self.bot, player)

        view = HostLobby(game, player)
        embed = EmbedGen.FullEmbed(
            title = f"{game.mode.name.title()} Lobby",
            fields = [EmbedGen.EmbedField(name = "Players", value = "1", inline = True)],
        )
        await interaction.response.send_message(view = view, embed = embed, ephemeral = True)
        view.response = await interaction.original_response()
        player.view = view

        message = await interaction.followup.send(f"{interaction.user.mention} has started a {game.mode.name.title()} lobby\nJoin it using {Converters.to_command_mention(self.join_lobby, interaction.guild)}", wait = True, silent = True)
        await sleep(30)
        await message.delete()

    @app_commands.command(name = "join")
    async def join_lobby(self, interaction: Interaction, game: Games, bet: app_commands.Range[int, 100, 100_000]):
        """Join an existing gambling game using WorstCoin

        :param interaction:
        :param game: Game to join
        :param bet: Amount of WorstCoin to bet: 100-100,000
        :return:
        """
        wealth = await get_wealth(self.bot, interaction.guild, interaction.user)
        if interaction.guild not in self.games:
            self.games[interaction.guild] = {}

        if game not in self.games[interaction.guild]:
            return await interaction.response.send_message(f"{game.name.title()} lobby not open, start one with {Converters.to_command_mention(self.start_lobby, interaction.guild)}", ephemeral = True)
        elif self.games[interaction.guild][game].state is (GameState.cancelled, GameState.finished):
            return await interaction.response.send_message(f"{game.name.title()} lobby cancelled, start a new one with {Converters.to_command_mention(self.start_lobby, interaction.guild)}", ephemeral = True)
        elif self.games[interaction.guild][game].state is GameState.playing:
            return await interaction.response.send_message(f"{game.name.title()} lobby already playing, please wait for it to finish", ephemeral = True)
        elif wealth.wallet < bet:
            return await interaction.response.send_message(f"You need at least {bet} WorstCoin to join a lobby with this bet", ephemeral = True)

        player = await self.games[interaction.guild][game].add_player(wealth, bet)
        view = GuestLobby(self.games[interaction.guild][game], player)
        embed = EmbedGen.FullEmbed(
            title = f"{game.name.title()} Lobby",
            fields = [EmbedGen.EmbedField(name = "Players", value = len(
                self.games[interaction.guild][game].players), inline = True)],
        )
        await interaction.response.send_message(view = view, embed = embed, ephemeral = True)
        view.response = await interaction.original_response()
        player.view = view


async def setup(bot):
    await bot.add_cog(Gambling(bot))
