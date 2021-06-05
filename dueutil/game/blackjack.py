from pydealer.deck import Deck

equivalents = {
    "Jack": 10,
    "Queen": 10,
    "King": 10,
    "Ace": 11
}


def get_deck_value(deck: Deck):
    value = 0
    aces = 0

    for card in deck:
        if card.value not in equivalents:
            value += int(card.value)
        else:
            value += equivalents[card.value]

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
    deck1Value = get_deck_value(deck1)
    deck2Value = get_deck_value(deck2)

    return deck1Value, deck2Value
