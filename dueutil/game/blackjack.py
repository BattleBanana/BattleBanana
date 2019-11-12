import pydealer

equivalents = {
    "Jack": 10,
    "Queen": 10,
    "King": 10
}

def compare_decks(deck1, deck2):
    """
    return deck's value
    """
    deck1Value = 0
    deck2Value = 0
    specials = []
    for card in deck1:
        if card.value == "Ace":
            specials.append(card)
            continue
        try:
            deck1Value += int(card.value)
        except ValueError:
            deck1Value += equivalents.get(card.value)
    for card in specials:
        if deck1Value + 11 > 21:
            deck1Value += 1
        else:
            deck1Value += 11
            
    specials.clear()
    for card in deck2:
        if card.value == "Ace":
            specials.append(card)
            continue
        try:
            deck2Value += int(card.value)
        except ValueError:
            deck2Value += equivalents.get(card.value)
    for card in specials:
        if deck2Value + 11 > 21:
            deck2Value += 1
        else:
            deck2Value += 11
    
    return deck1Value, deck2Value