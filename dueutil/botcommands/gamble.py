import os
import re
import subprocess
import math
import time
from io import StringIO
import random
import asyncio

from pydealer import Deck

import discord
import objgraph

import generalconfig as gconf
import dueutil.permissions
from ..game.helpers import imagehelper
from ..permissions import Permission
from .. import commands, util, events, dbconn
from ..game import players, emojis as e
from ..game import blackjack as blackjackGame

"""
This is a super cool category with some ~~gambling~~ surprise mechanics. 

Have fun kiddos!
"""

@commands.command(args_pattern="I", aliases=["bj"])
@commands.ratelimit(cooldown=5, error="You can't use blackjack again for **[COOLDOWN]**!", save=True)
async def blackjack(ctx, price, **details):
    """
    [CMD_KEY]blackjack (bet)
    
    Play blackjack with BattleBanana.
    
    Game objective: Obtain 21 or the closest to win!
    [Card Values](https://battlebanana.xyz/img/21Values.png)
    """
    user = details["author"]
    
    if user.money < price:
        raise util.DueUtilException(ctx.channel, "You cannot bet that much!")
    if price < 1:
        raise util.DueUtilException(ctx.channel, "You cannot bet under ¤1")
    if (user.gamble_play and int(time.time() - user.last_played) < 120) or int(time.time() - user.last_played) < 120:
        raise util.DueUtilException(ctx.channel, "You are already playing!")
    
    
    # Create new deck, make player playing
    deck = Deck() + Deck() + Deck() + Deck()
    deck.shuffle()
    user.gamble_play = True
    user.last_played = time.time()
    gain = 0
    
    # Hands out 2 cards to each & calculate the count
    dealer_hand = deck.deal(2)
    user_hand = deck.deal(2)
    user_value, dealer_value = blackjackGame.compare_decks(user_hand, dealer_hand)
    
    blackjack_embed = discord.Embed(title="Blackjack dealer", description="%s game. Current bet: ¤%s" 
                                    % (user.get_name_possession(), price), type="rich", colour=gconf.DUE_COLOUR)
    blackjack_embed.add_field(name="Your hand (%s)" % (user_value), value=user_hand)
    blackjack_embed.add_field(name="Dealer's hand (%s)" % (dealer_value), value=dealer_hand)
    blackjack_embed.set_footer(text="Reply with \"hit\" or \"stand\". This prompt will close in 120 seconds")
    
    msg = await util.say(ctx.channel, embed=blackjack_embed)
    # Player's play
    while True:
        user.last_played = time.time()
        user_value, dealer_value = blackjackGame.compare_decks(user_hand, dealer_hand)
        if user_value >= 21 or dealer_value >= 21:
            break
        user_msg = await util.wait_for_message(ctx)
        
        if user_msg != None and user_msg.content.lower() == "hit":
            user_hand += deck.deal(1)
            user_value, dealer_value = blackjackGame.compare_decks(user_hand, dealer_hand)
            
            blackjack_embed.clear_fields()
            blackjack_embed.add_field(name="Your hand (%s)" % (user_value), value=user_hand)
            blackjack_embed.add_field(name="Dealer's hand (%s)" % (dealer_value), value=dealer_hand)
            
            await util.edit_message(msg, embed=blackjack_embed)
            
            await util.delete_message(user_msg)
        else:
            if user_msg:
                await util.delete_message(user_msg)
            break
        
    # Dealer's turn
    while True:
        user_value, dealer_value = blackjackGame.compare_decks(user_hand, dealer_hand)
        if dealer_value >= 21 or user_value > 21 or dealer_value > user_value:
            break
        if dealer_value < 17: # Make him pick a card
            dealer_hand += deck.deal(1)
        else:
            break
    

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
            result = "You win with an hand of %s against %s" % (user_value, dealer_value)
    elif user_value < dealer_value:
        if dealer_value > 21:
            if user_value == 21: # If you have 21 and dealer busted
                gain += price * 1.5
            else:
                gain += price
            result = "Dealer busted!"
        elif dealer_value == 21:
            gain -= price
            result = "Dealer win with a blackjack!"
        else:
            gain -= price
            result = "Dealer win with an hand of %s against %s" % (dealer_value, user_value)
    else:
        result = "This is a tie! %s-%s" % (user_value, dealer_value)
    
    # Manage the message
    gain = math.floor(gain)
    user.money += gain
    if gain > 0:
        result += " You were rewarded with `¤%s`" % (gain)
    elif gain < 0:
        result += " You lost `¤%s`." % (price)
    else:
        result += " You got your bet back!"
    
    blackjack_embed.clear_fields()
    blackjack_embed.add_field(name="Your hand (%s)" % (user_value), value=user_hand)
    blackjack_embed.add_field(name="Dealer's hand (%s)" % (dealer_value), value=dealer_hand)
    blackjack_embed.add_field(name="Result", value=result, inline=False)
    blackjack_embed.set_footer()
    
    user.command_rate_limits['blackjack_saved_cooldown'] = int(time.time())
    user.gamble_play = False
    user.last_played = 0
    user.save()
    
    await util.edit_message(msg, embed=blackjack_embed)

@commands.command(args_pattern="I", aliases=["rr"])
@commands.ratelimit(cooldown=5, error="You can't use russian roulette again for **[COOLDOWN]**!", save=True)
async def russianroulette(ctx, price, **details):
    """
   [CMD_KEY]rusaianroulette ~~(bet)~~
    
    Play Russian Roulette with your friends, the gun.
    
    Game objective: Pray to survive.
    """

    user = details["author"]
    
    if user.money < price:
       raise util.DueUtilException(ctx.channel, "You cannot bet that much!")
    if price < 1:
       raise util.DueUtilException(ctx.channel, "You cannot bet under ¤1")
    
    message = await util.say(ctx.channel, "Click...")
    rnd = random.randint(1, 6)
    await asyncio.sleep(random.random() * 2)
    if rnd == 1:
        reward = price * 10
        user.money += reward
        await util.edit_message(message, content=message.content + "\nYou survived and won `¤%s`!" % (reward))
    else:
        user.money -= price
        await util.edit_message(message, content=message.content + "\nYou died and lost `¤%s`!" % (price))
    user.save()
