import discord
from discord import ButtonStyle, ui
from pydealer.card import Card
from pydealer.const import DEFAULT_RANKS
from pydealer.const import VALUES as CARDS
from pydealer.deck import Deck

DEFAULT_TIMEOUT = 120

EQUIVALENTS = {"Jack": 10, "Queen": 10, "King": 10, "Ace": 11}

RTB_COLORS = {
    "red": ["Hearts", "Diamonds"],
    "black": ["Spades", "Clubs"],
}

RTB_EQUIVALENTS = {
    "Ace": 1,
    "Jack": 11,
    "Queen": 12,
    "King": 13,
}


class BlackjackInteraction(ui.View):
    """
    Interaction for blackjack game

    Args:
        author (discord.User): The author of the interaction
        timeout (int, optional): The timeout of the interaction. Defaults to 120.
    """

    def __init__(self, author: discord.User, timeout=DEFAULT_TIMEOUT):
        self._author = author
        self.value = "stand"
        super().__init__(timeout=timeout)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self._author.id:
            return True

        await interaction.response.send_message("This is not your game!", ephemeral=True)

        return False

    async def start(self):
        await self.wait()
        return self.value

    @ui.button(label="Hit", style=ButtonStyle.primary)
    async def hit(self, interaction: discord.Interaction, _: ui.Button):
        await interaction.response.defer()
        self.value = "hit"
        self.stop()

    @ui.button(label="Stand", style=ButtonStyle.primary)
    async def stand(self, interaction: discord.Interaction, _: ui.Button):
        await interaction.response.defer()
        self.value = "stand"
        self.stop()


class CardSelection(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=rank, value=rank) for rank in CARDS]
        super().__init__(
            placeholder="Choose the card rank...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        # When a card is selected, we set the view's value and stop the interaction.
        self.view.value = f"{self.values[0]}"
        await interaction.response.defer()
        self.view.stop()


class RideTheBusButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str):
        super().__init__(label=label, style=discord.ButtonStyle.primary, custom_id=custom_id)

    async def callback(self, interaction: discord.Interaction):
        # When a button is clicked, we set the view's value and stop the interaction.
        self.view.value = self.custom_id
        await interaction.response.defer()
        self.view.stop()


class RideTheBusInteraction(discord.ui.View):
    """
    Interaction for ride the bus game

    Args:
        author (discord.User): The author of the interaction
        step (int): The current step of the game
        timeout (int, optional): The timeout of the interaction. Defaults to 120.
    """

    def __init__(self, author: discord.User, step: int, choices: list[str], *, timeout=120):
        self._author = author
        self.value = None
        super().__init__(timeout=timeout)

        if step == 1:
            self.remove_item(self.children[0])

        self._add_components(choices)

    def _add_components(self, choices: list[str]):
        for choice in choices:
            self.add_item(RideTheBusButton(label=choice, custom_id=choice.lower()))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self._author.id:
            return True

        await interaction.response.send_message("This is not your game!", ephemeral=True)
        return False

    async def start(self):
        await self.wait()
        return self.value

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.danger)
    async def btn_stop(self, interaction: discord.Interaction, _: discord.ui.Button):
        await interaction.response.defer()
        self.value = None
        self.stop()


def get_deck_value(deck: Deck):
    value = 0
    aces = 0

    for card in deck:
        if card.value not in EQUIVALENTS:
            value += int(card.value)
        else:
            value += EQUIVALENTS[card.value]

        if card.value == "Ace":
            aces += 1

    for _ in range(aces):
        if value > 21:
            value -= 10
        else:
            break

    return value


def compare_decks(deck1: Deck, deck2: Deck):
    """
    return deck's value
    """
    deck1_value = get_deck_value(deck1)
    deck2_value = get_deck_value(deck2)

    return deck1_value, deck2_value


class RideTheBusValidators:
    @staticmethod
    def validate_red_black(card: Card, choice: str) -> bool:
        card_colour = "red" if card.suit in RTB_COLORS["red"] else "black"

        return choice == card_colour

    @staticmethod
    def validate_higher_lower(card: Card, previous_card: Card, choice: str) -> bool:
        card_value = DEFAULT_RANKS["values"][card.value]
        previous_card_value = DEFAULT_RANKS["values"][previous_card.value]

        return (choice == "higher" and card_value > previous_card_value) or (
            choice == "lower" and card_value < previous_card_value
        )

    @staticmethod
    def validate_in_between(card: Card, card1: Card, card2: Card, choice: str) -> bool:
        card_value = DEFAULT_RANKS["values"][card.value]
        low = min(DEFAULT_RANKS["values"][card1.value], DEFAULT_RANKS["values"][card2.value])
        high = max(DEFAULT_RANKS["values"][card1.value], DEFAULT_RANKS["values"][card2.value])

        return (choice == "in-between" and low < card_value < high) or (
            choice == "outside" and (card_value < low or card_value > high)
        )

    @staticmethod
    def validate_suit_guess(card: Card, choice: str) -> bool:
        return card.suit.lower() == choice.lower()
