import math
import time
import random
import asyncio

from pydealer import Deck

import discord

import generalconfig as gconf
from .. import commands, util
from ..game import blackjack as blackjackGame, players, translations

"""
This is a super cool category with some ~~gambling~~ surprise mechanics. 

Have fun kiddos!
"""

@commands.command(args_pattern="I", aliases=["bj"])
@commands.ratelimit(cooldown=5, error="gamble:blackjack:RateLimit", save=True)
async def blackjack(ctx, price, **details):
    """gamble:blackjack:Help"""
    user = details["author"]
    BattleBanana = players.find_player(ctx.guild.me.id)
    
    if user.money < price or price > 1000000000:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "gamble:blackjack:HighBet"))
    if price < 1:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "gamble:blackjack:LowBet"))
    if (user.gamble_play and int(time.time() - user.last_played) < 120) or int(time.time() - user.last_played) < 120:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "gamble:blackjack:AlreadyPlay"))
    
    
    # Create new deck, make player playing
    deck = Deck() + Deck() + Deck() + Deck()
    deck.shuffle()
    user.gamble_play = True
    user.last_played = time.time()
    
    # Hands out 2 cards to each & calculate the count
    dealer_hand = deck.deal(2)
    user_hand = deck.deal(2)
    user_value, dealer_value = blackjackGame.compare_decks(user_hand, dealer_hand)
    
    blackjack_embed = discord.Embed(title=translations.translate(ctx,"gamble:blackjack:StartTitle"), description=translations.translate(ctx,"gamble:blackjack:StartDesc", user.get_name_possession(), price), type="rich", colour=gconf.DUE_COLOUR)
    blackjack_embed.add_field(name=translations.translate(ctx, "gamble:blackjack:UserHand", user_value), value=user_hand)
    blackjack_embed.add_field(name=translations.translate(ctx, "gamble:blackjack:DealerHand", dealer_value), value=dealer_hand)        
    blackjack_embed.set_footer(text=translations.translate(ctx, "gamble:blackjack:StartFooter"))
    
    msg = await util.reply(ctx, embed=blackjack_embed)
    # Player's play
    while True:
        user.last_played = time.time()
        user_value, dealer_value = blackjackGame.compare_decks(user_hand, dealer_hand)
        if user_value >= 21 or dealer_value >= 21:
            break
        user_msg = await util.wait_for_message(ctx, ctx.author)
        
        if user_msg != None and user_msg.content.lower() == "hit":
            user_hand += deck.deal(1)
            user_value, dealer_value = blackjackGame.compare_decks(user_hand, dealer_hand)
            
            blackjack_embed.clear_fields()
            blackjack_embed.add_field(name=translations.translate(ctx, "gamble:blackjack:UserHand", user_value), value=user_hand)
            blackjack_embed.add_field(name=translations.translate(ctx, "gamble:blackjack:DealerHand", dealer_value), value=dealer_hand)
            
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
            result = translations.translate(ctx, "gamble:blackjack:UserBust")
        elif user_value == 21:
            gain += price * 1.5
            result = translations.translate(ctx, "gamble:blackjack:UserBJ")
        else:
            gain += price
            result = translations.translate(ctx, "gamble:blackjack:UserWin", user_value, dealer_value)
    elif user_value < dealer_value:
        if dealer_value > 21:
            if user_value == 21: # If you have 21 and dealer busted
                gain += price * 1.5
            else:
                gain += price
            result = translations.translate(ctx, "gamble:blackjack:DealBust")
        elif dealer_value == 21:
            gain -= price
            result = translations.translate(ctx, "gamble:blackjack:DealBJ")
        else:
            gain -= price
            result = translations.translate(ctx, "gamble:blackjack:DealWin", dealer_value, user_value)
    else:
        result =  translations.translate(ctx, "gamble:blackjack:Tie", user_value, dealer_value)
    
    # Manage the message
    gain = math.floor(gain)
    user.money += gain
    if gain > 0:
        result += translations.translate(ctx, "gamble:blackjack:RewardWin", price+gain)
    elif gain < 0:
        result += translations.translate(ctx, "gamble:blackjack:RewardLose", price)
        BattleBanana.money += price
    else:
        result += translations.translate(ctx, "gamble:blackjack:RewardTie")
    
    blackjack_embed.clear_fields()
    blackjack_embed.add_field(name=translations.translate(ctx, "gamble:blackjack:UserHand", user_value), value=user_hand)
    blackjack_embed.add_field(name=translations.translate(ctx, "gamble:blackjack:DealerHand", dealer_value), value=dealer_hand)
    blackjack_embed.add_field(name=translations.translate(ctx, "gamble:blackjack:Result"), value=result, inline=False)
    blackjack_embed.set_footer()
    
    user.command_rate_limits['blackjack_saved_cooldown'] = int(time.time())
    user.gamble_play = False
    user.last_played = 0
    user.save()
    BattleBanana.save()
    
    await util.edit_message(msg, embed=blackjack_embed)

@commands.command(args_pattern="I", aliases=["rr"])
@commands.ratelimit(cooldown=5, error="gamble:russianroulette:RateLimit", save=True)
async def russianroulette(ctx, price, **details):
    """gamble:russianroulette:Help"""

    user = details["author"]
    BattleBanana = players.find_player(ctx.guild.me.id)
    
    if user.money < price or price > 1000000000:
       raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "gamble:russianroulette:TooHigh"))
    if price < 1:
       raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "gamble:russianroulette:TooLow"))
    
    message = await translations.say(ctx, "gamble:russianroulette:Click")
    rnd = random.randint(1, 6)
    await asyncio.sleep(random.random() * 2)
    if rnd == 1:
        reward = price * 5
        user.money += reward
        await util.edit_message(message, content=message.content + translations.translate(ctx, "gamble:russianroulette:Win", reward))
    else:
        user.money -= price
        BattleBanana.money += price
        await util.edit_message(message, content=message.content + translations.translate(ctx, "gamble:russianroulette:Lose", price))
    user.save()
    BattleBanana.save()
