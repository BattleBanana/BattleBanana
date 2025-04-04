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
from pydealer import Deck

import generalconfig as gconf
from dueutil import commands, util
from dueutil.game import blackjack as blackjackGame
from dueutil.game import players, stats


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
    user_value, dealer_value = blackjackGame.compare_decks(user_hand, dealer_hand)

    blackjack_embed = discord.Embed(
        title="Blackjack dealer",
        description=f"{player.get_name_possession()} game. Current bet: ¤{price}",
        type="rich",
        colour=gconf.DUE_COLOUR,
    )
    blackjack_embed.add_field(name=f"Your hand ({user_value})", value=user_hand)
    blackjack_embed.add_field(name=f"Dealer's hand ({dealer_value})", value=dealer_hand)
    blackjack_embed.set_footer(text='Click on "hit" or "stand". This prompt will close in 120 seconds')

    blackjack_buttons: ui.View = blackjackGame.BlackjackInteraction(ctx.author)
    msg = await util.reply(ctx, embed=blackjack_embed, view=blackjack_buttons)

    while user_value < 21 and dealer_value < 21:
        player.last_played = time.time()

        player.command_rate_limits["blackjack_saved_cooldown"] = int(time.time()) + 120
        content = await blackjack_buttons.start()
        if content == "hit":
            user_hand += deck.deal(1)
            user_value = blackjackGame.get_deck_value(user_hand)

            blackjack_embed.clear_fields()
            blackjack_embed.add_field(name=f"Your hand ({user_value})", value=user_hand)
            blackjack_embed.add_field(name=f"Dealer's hand ({dealer_value})", value=dealer_hand)

            blackjack_buttons = blackjackGame.BlackjackInteraction(ctx.author)
            await msg.edit(embed=blackjack_embed, view=blackjack_buttons)
        elif content == "stand":
            break

    # Dealer's turn
    while dealer_value < 17 and user_value <= 21:
        # Make him pick a card
        dealer_hand += deck.deal()

        dealer_value = blackjackGame.get_deck_value(dealer_hand)

    # Manage who wins/loses
    user_value, dealer_value = blackjackGame.compare_decks(user_hand, dealer_hand)
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
        reward = price * 5
        player.money += reward
        stats.increment_stat(stats.Stat.MONEY_GENERATED, reward, source="russianroulette") # gamble tax when
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
