"""
This is a super cool category with some ~~gambling~~ surprise mechanics.

Have fun kiddos!
"""

import asyncio
import math
import random
import secrets
import time

import discord
from discord import ui
from pydealer import SUITS, VALUES, Deck

import generalconfig as gconf
from dueutil import commands, util
from dueutil.game import gamble, players, stats
from dueutil.game.gamble import RideTheBusValidators


@commands.command(args_pattern="I", aliases=["bj"])
@commands.ratelimit(cooldown=5, error="You can use blackjack again **[COOLDOWN]**!", save=True)
async def blackjack(ctx, price, **details):
    """
    [CMD_KEY]blackjack (bet)

    Play blackjack with BattleBanana.

    Game objective: Obtain 21 or the closest to win!
    [Card Values](https://battlebanana.xyz/img/21Values.png)
    """
    if price < 1:
        raise util.BattleBananaException(ctx.channel, "You cannot bet under ¤1")

    player = details["author"]
    if price > player.money:
        raise util.BattleBananaException(ctx.channel, "You cannot bet more than you have!")

    player.command_rate_limits["blackjack_saved_cooldown"] = int(time.time()) + 120

    # Create new deck, make player playing
    deck = Deck() + Deck() + Deck() + Deck()
    deck.shuffle(5)

    # Hands out 2 cards to each & calculate the count
    dealer_hand = deck.deal(2)
    user_hand = deck.deal(2)
    user_value, dealer_value = gamble.compare_decks(user_hand, dealer_hand)

    blackjack_embed = discord.Embed(
        title="Blackjack dealer",
        description=f"{player.get_name_possession()} game. Current bet: ¤{price}",
        type="rich",
        colour=gconf.DUE_COLOUR,
    )
    blackjack_embed.add_field(name=f"Your hand ({user_value})", value=user_hand)
    blackjack_embed.add_field(name=f"Dealer's hand ({dealer_value})", value=dealer_hand)
    blackjack_embed.set_footer(text='Click on "hit" or "stand". This prompt will close in 120 seconds')

    blackjack_buttons: ui.View = gamble.BlackjackInteraction(ctx.author)
    msg = await util.reply(ctx, embed=blackjack_embed, view=blackjack_buttons)

    while user_value < 21 and dealer_value < 21:
        player.last_played = time.time()

        player.command_rate_limits["blackjack_saved_cooldown"] = int(time.time()) + 120
        content = await blackjack_buttons.start()
        if content == "hit":
            user_hand += deck.deal(1)
            user_value = gamble.get_deck_value(user_hand)

            blackjack_embed.clear_fields()
            blackjack_embed.add_field(name=f"Your hand ({user_value})", value=user_hand)
            blackjack_embed.add_field(name=f"Dealer's hand ({dealer_value})", value=dealer_hand)

            blackjack_buttons = gamble.BlackjackInteraction(ctx.author)
            await msg.edit(embed=blackjack_embed, view=blackjack_buttons)
        elif content == "stand":
            break

    # Dealer's turn
    while dealer_value < 17 and user_value <= 21:
        # Make him pick a card
        dealer_hand += deck.deal()

        dealer_value = gamble.get_deck_value(dealer_hand)

    # Manage who wins/loses
    user_value, dealer_value = gamble.compare_decks(user_hand, dealer_hand)
    gain = 0
    if user_value > dealer_value:
        if user_value > 21:
            gain -= price
            result = "You busted!"
        elif user_value == 21:
            gain += price * 1.5
            result = "You win with a blackjack!"
        else:
            gain += price
            result = f"You win with an hand of {user_value} against {dealer_value}."
    elif user_value < dealer_value:
        if dealer_value > 21:
            if user_value == 21:  # If you have 21 and dealer busted
                gain += price * 1.5
            else:
                gain += price
            result = "Dealer busted!"
        elif dealer_value == 21:
            gain -= price
            result = "Dealer win with a blackjack!"
        else:
            gain -= price
            result = f"Dealer win with an hand of {dealer_value} against {user_value}."
    else:
        result = f"This is a tie! {user_value}-{dealer_value}"

    # Manage the message
    gain = math.floor(gain)
    player.money += gain
    player.command_rate_limits["blackjack_saved_cooldown"] = int(time.time())
    player.save()

    if gain > 0:
        result += f" You were rewarded with `¤{gain}`"
        stats.increment_stat(stats.Stat.MONEY_GENERATED, gain, source="blackjack")
    elif gain < 0:
        result += f" You lost `¤{price}`."
        stats.increment_stat(stats.Stat.MONEY_REMOVED, price, source="blackjack")

        battle_banana = players.find_player(ctx.guild.me.id)
        if battle_banana is not None:
            battle_banana.money += price
            battle_banana.save()
    else:
        result += " You got your bet back!"

    blackjack_embed.clear_fields()
    blackjack_embed.add_field(name=f"Your hand ({user_value})", value=user_hand)
    blackjack_embed.add_field(name=f"Dealer's hand ({dealer_value})", value=dealer_hand)
    blackjack_embed.add_field(name="Result", value=result, inline=False)
    blackjack_embed.set_footer()

    blackjack_buttons.clear_items()
    await msg.edit(embed=blackjack_embed, view=None)


@commands.command(args_pattern="I", aliases=["rr"])
@commands.ratelimit(cooldown=5, error="You can use russian roulette again **[COOLDOWN]**!", save=True)
async def russianroulette(ctx, price, **details):
    """
    [CMD_KEY]russianroulette (bet)

     Play Russian Roulette with your friends, the gun.

     Game objective: Pray to survive.
    """
    if price < 1:
        raise util.BattleBananaException(ctx.channel, "You cannot bet under ¤1")

    player = details["author"]
    if price > player.money:
        raise util.BattleBananaException(ctx.channel, "You cannot bet more than you have!")

    message = await util.reply(ctx, "Click...")
    await asyncio.sleep(random.random() * 2)
    if secrets.randbelow(6) == 1:
        reward = price * 4
        player.money += reward
        stats.increment_stat(stats.Stat.MONEY_GENERATED, reward, source="russianroulette")  # gamble tax when
        await message.edit(content=message.content + f"\nYou survived and won `¤{reward}`!")
    else:
        player.money -= price
        stats.increment_stat(stats.Stat.MONEY_REMOVED, price, source="russianroulette")
        battle_banana = players.find_player(ctx.guild.me.id)
        if battle_banana is not None:
            battle_banana.money += price
            battle_banana.save()
        await message.edit(content=message.content + f"\nYou died and lost `¤{price}`!")
    player.save()


@commands.command(args_pattern="I", aliases=["rtb"])
@commands.ratelimit(cooldown=5, error="You can use ride the bus again **[COOLDOWN]**!", save=True)
async def ridethebus(ctx, price, **details):
    """
    [CMD_KEY]ridethebus (bet)

    Play Ride the Bus with your very own chauffeur, BattleBanana.

    Game objective: Ride the bus until the end!

    Game Rules:
    - Step 1: Guess the color of the card (Red or Black)
      - Reds are Hearts and Diamonds
      - Blacks are Spades and Clubs
    - Step 2: Guess if the next card is higher or lower than the previous card
      - Lowest card is a 2
      - Highest card is an Ace
    - Step 3: Guess if the next card is in-between or outside the previous two cards
    - Step 4: Guess the suit of the next card

    Reward multipliers (highest step reached):
    - Step 1: Red/Black (0.65x)
    - Step 2: Higher/Lower (1.30x)
    - Step 3: In-Between/Outside (1.75x)
    - Step 4: Suit Guess (5.30x)
    """

    if price < 1:
        raise util.BattleBananaException(ctx.channel, "You cannot bet under ¤1")

    player = details["author"]
    if price > player.money:
        raise util.BattleBananaException(ctx.channel, "You cannot bet more than you have!")

    deck = Deck() + Deck() + Deck() + Deck()
    deck.shuffle(5)

    steps = {
        1: {
            "name": "Red/Black",
            "choices": ["Red", "Black"],
            "multiplier": 0.65,
        },
        2: {
            "name": "Higher/Lower",
            "choices": ["Higher", "Lower"],
            "multiplier": 1.30,
        },
        3: {
            "name": "In-Between/Outside",
            "choices": ["In-Between", "Outside"],
            "multiplier": 1.75,
        },
        4: {
            "name": "Suit Guess",
            "choices": ["Hearts", "Diamonds", "Clubs", "Spades"],
            "multiplier": 5.30,
        },
    }

    embed = discord.Embed(
        title="Ride the Bus",
        description=f"Bet: **¤{price}**\nGet ready to ride the bus!",
        colour=gconf.DUE_COLOUR,
    )
    message = await util.reply(ctx, embed=embed)

    dealt_cards = []
    last_multiplier = 0.0

    for step, step_data in steps.items():
        current_multiplier = step_data["multiplier"]
        cards_text = f"\nCards drawn: {", ".join(str(card) for card in dealt_cards)}" if dealt_cards else ""
        embed.title = f"Ride the Bus - Step {step}: {step_data["name"]}"
        payout_line = (
            f"Current Payout (if you stop here): **¤{math.floor(price * last_multiplier)}**\n" if step > 1 else ""
        )
        embed.description = (
            f"Bet: **¤{price}**\n" f"{payout_line}" f"**{step_data["name"]}**: Make your choice!{cards_text}"
        )

        view = gamble.RideTheBusInteraction(ctx.author, step=step, choices=step_data["choices"])
        await message.edit(embed=embed, view=view)
        await view.wait()

        if view.value is None:
            break

        choice = view.value
        card = deck.deal(1)[0]

        valid = False
        if step == 1:
            valid = RideTheBusValidators.validate_red_black(card, choice)
        elif step == 2:
            valid = RideTheBusValidators.validate_higher_lower(card, dealt_cards[0], choice)
        elif step == 3:
            valid = RideTheBusValidators.validate_in_between(card, dealt_cards[0], dealt_cards[1], choice)
        elif step == 4:
            valid = RideTheBusValidators.validate_suit_guess(card, choice)

        dealt_cards.append(card)

        if not valid:
            step_one_color_hint = ""
            if step == 1:
                step_one_color = "Red" if card.suit in gamble.RTB_COLORS["red"] else "Black"
                step_one_color_hint = f" ({step_one_color})"

            embed.title = "Ride the Bus - Game Over"
            embed.description = (
                f"You chose **{choice.title()}** but drew **{card}{step_one_color_hint}**!\n" f"You lost **¤{price}**."
            )
            embed.colour = discord.Colour.red()
            await message.edit(embed=embed, view=None)

            player.money -= price
            player.save()
            stats.increment_stat(stats.Stat.MONEY_REMOVED, price, source="ridethebus")
            battle_banana = players.find_player(ctx.guild.me.id)
            if battle_banana is not None:
                battle_banana.money += price
                battle_banana.save()
            return

        last_multiplier = current_multiplier

    if last_multiplier == 0.0:
        embed.title = "Ride the Bus"
        embed.description = "The bus ride ended before it started. No money was lost."
        await message.edit(embed=embed, view=None)
        return

    final_payout = math.floor(price * last_multiplier)
    gain = final_payout - price
    player.money += gain
    player.save()

    if gain > 0:
        stats.increment_stat(stats.Stat.MONEY_GENERATED, gain, source="ridethebus")
        embed.colour = discord.Colour.green()
    elif gain < 0:
        stats.increment_stat(stats.Stat.MONEY_REMOVED, abs(gain), source="ridethebus")
        embed.colour = discord.Colour.red()
        battle_banana = players.find_player(ctx.guild.me.id)
        if battle_banana is not None:
            battle_banana.money += abs(gain)
            battle_banana.save()
    else:
        embed.colour = discord.Colour.green()

    embed.title = "Ride the Bus - Result"
    embed.description = (
        f"Multiplier: **{last_multiplier}x**\n"
        f"Cards drawn:\n- {"\n- ".join(str(card) for card in dealt_cards)}\n"
        f"{"Won" if gain >= 0 else "Lost"}: **¤{abs(gain)}**"
    )
    await message.edit(embed=embed, view=None)
