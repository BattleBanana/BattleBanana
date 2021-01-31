from datetime import datetime

import discord
import repoze.timeago
import asyncio

import generalconfig as gconf
from .. import commands, util, dbconn
from ..game import awards, players, leaderboards, battles, translations
from ..game.helpers import misc, imagehelper
from ..game import emojis

topdogs_per_page = 10


async def glitter_text(ctx, text):
    try:
        gif_text = await misc.get_glitter_text(text)
        await ctx.channel.send(file=discord.File(fp=gif_text, filename="glittertext.gif"), content=":sparkles: "+translations.translate(ctx, "fun:glitter:Content"))
    except (ValueError, asyncio.TimeoutError):
        await translations.say(ctx, "fun:glitter:Error")


@commands.command(args_pattern='S', aliases=("gt", "glittertext",))
@commands.imagecommand()
async def glitter(ctx, text, **details):
    """fun:glitter:Help"""
    details["author"].misc_stats["art_created"] += 1
    await glitter_text(ctx, text)


@commands.command(args_pattern="S?")
@commands.imagecommand()
async def eyes(ctx, eye_description="", **details):
    """
    [CMD_KEY]eyes modifiers
    
    __Modifiers:__
        snek - Snek eyes (slits)
        ogre - Ogre colours
        evil - Red eyes
        gay  - Pink stuff
        high - Large pupils + red eyes
        emoji - emoji size + no border
        small - Small size (larger than emoji)
        left - Eyes look left
        right - Eyes look right
        top - Eyes look to the top
        bottom - Eyes look to the bottom
        derp - Random pupil positions
        bottom left - Eyes look bottom left
        bottom right - Eyes look bottom right
        top right - Eyes look top right
        top left - Eyes look top left
        no modifiers - Procedurally generated eyes!!!111
    """
    details["author"].misc_stats["art_created"] += 1
    await imagehelper.googly_eyes(ctx, eye_description)


@commands.command(args_pattern="C?", aliases=("globalrankings", "globalleaderboard", "gleaderboard"))
async def globalranks(ctx, page=1, **details):
    """
    [CMD_KEY]globalranks (page)

    Global BattleBanana leaderboard
    """

    await leaderboard.__wrapped__(ctx, mixed="global", page_alt=page, **details)


@commands.command(args_pattern="M?C?", aliases=("ranks", "rankings"))
async def leaderboard(ctx, mixed=1, page_alt=1, **details):
    """
    [CMD_KEY]leaderboard (page)
    or for global ranks
    [CMD_KEY]leaderboard global (page)
    [CMD_KEY]globalranks (page)
    
    The global leaderboard of BattleBanana!
    
    The leaderboard updated every hour*.
    
    **Now with local**

    *May be longer.
    
    """

    page_size = 10

    # Handle weird page args
    if type(mixed) is int:
        page = mixed - 1
        local = True
        ranks = "local"
    else:
        local = mixed.lower() != "global"
        ranks = "local" if local else "global"
        page = page_alt - 1

    # Local/Global
    if local:
        title = "BattleBanana Leaderboard on %s" % details["server_name_clean"]
        # Cached.
        local_leaderboard = leaderboards.get_local_leaderboard(ctx.guild, "levels")
        leaderboard_data = local_leaderboard.data
        last_updated = local_leaderboard.updated
    else:
        title = "BattleBanana Global Leaderboard"
        leaderboard_data = leaderboards.get_leaderboard("levels")
        last_updated = leaderboards.last_leaderboard_update

    if leaderboard_data is None or len(leaderboard_data) == 0:
        await util.reply(ctx, "The %s leaderboard has yet to be calculated!\n" % ranks
                       + "Check again soon!")
        return

    leaderboard_embed = discord.Embed(title="%s %s" % (emojis.QUESTER, title),
                                      type="rich", color=gconf.DUE_COLOUR)

    if page > 0:
        leaderboard_embed.title += ": Page %d" % (page + 1)
    if page * page_size >= len(leaderboard_data):
        raise util.BattleBananaException(ctx.channel, "Page not found")

    index = 0
    for index in range(page_size * page, page_size * page + page_size):
        if index >= len(leaderboard_data):
            break
        bonus = ""
        if index == 0:
            bonus = "     :first_place:"
        elif index == 1:
            bonus = "     :second_place:"
        elif index == 2:
            bonus = "     :third_place:"
        player = players.find_player(leaderboard_data[index])
        user_info = ctx.guild.get_member(player.id)
        if user_info is None:
            user_info = player.id
        leaderboard_embed \
            .add_field(name="#%s" % (index + 1) + bonus,
                       value="[%s **``Level %s``**](https://battlebanana.xyz/player/id/%s) (%s) | **Total EXP** %d"
                             % (player.name_clean, player.level, player.id,
                                util.ultra_escape_string(str(user_info)), player.total_exp), inline=False)

    if index < len(leaderboard_data) - 1:
        remaining_players = len(leaderboard_data) - page_size * (page + 1)
        leaderboard_embed.add_field(name="+%d more!" % remaining_players,
                                    value="Do ``%sleaderboard%s %d`` for the next page!"
                                          % (details["cmd_key"], "" if local else " global", page + 2), inline=False)
    leaderboard_embed.set_footer(text="Leaderboard calculated "
                                      + repoze.timeago.get_elapsed(datetime.utcfromtimestamp(last_updated)))
    await util.reply(ctx, embed=leaderboard_embed)


async def rank_command(ctx, player, ranks="", **details):
    ranks = ranks.lower()
    local = ranks != "global"

    if local:
        position = leaderboards.get_rank(player, "levels", ctx.guild)
        ranks = padding = ""
    else:
        position = leaderboards.get_rank(player, "levels")
        padding = " "

    player_is_author = ctx.author.id == player.id
    player_name = "**%s**" % player.name_clean

    if position != -1:
        page = position // 10 + (1 * position % 10 != 0)
        await util.reply(ctx, (":sparkles: " + ("You're" if player_is_author else player_name + " is")
                                     + (" **{0}** on the{4}{3} leaderboard!\n"
                                        + "That's on page {1} (``{2}leaderboard{4}{3} {5}``)!")
                                     .format(util.int_to_ordinal(position), page,
                                             details["cmd_key"], ranks, padding, page if page > 1 else "")))
    else:
        await util.reply(ctx, (":confounded: I can't find "
                                     + ("you" if player_is_author else player_name)
                                     + " on the {}{}leaderboard!?\n".format(ranks, padding)
                                     + "You'll need to wait till it next updates!" * player_is_author))


@commands.command(args_pattern="S?")
async def myrank(ctx, ranks="", **details):
    """
    [CMD_KEY]myrank
    or for your global rank
    [CMD_KEY]myrank global

    Tells you where you are on the [CMD_KEY]leaderboard.
    """

    await rank_command(ctx, details["author"], ranks, **details)


@commands.command(args_pattern="PS?")
async def rank(ctx, player, ranks="", **details):
    """
    [CMD_KEY]rank @player
    or for the global rank
    [CMD_KEY]rank @player global

    Tells you where a player is on the [CMD_KEY]leaderboard.
    """

    await rank_command(ctx, player, ranks, **details)


@commands.command(args_pattern="P?", aliases=("grank",))
async def globalrank(ctx, player=None, **details):
    """
    [CMD_KEY]globalrank
    or [CMD_KEY]globalrank @player

    Find your or another player's global rank.
    """

    if player is None:
        player = details["author"]
    await rank_command(ctx, player, "global", **details)


async def give_emoji(channel, sender, receiver, emoji):
    if not util.char_is_emoji(emoji) and not util.is_server_emoji(channel.guild, emoji):
        raise util.BattleBananaException(channel, "You can only send emoji!")
    if sender == receiver:
        raise util.BattleBananaException(channel, "You can't send a " + emoji + " to yourself!")
    await util.say(channel, "**" + receiver.name_clean + "** " + emoji + " :heart: **" + sender.name_clean + "**")


@commands.command(args_pattern='PS', aliases=("emoji",))
async def giveemoji(ctx, receiver, emoji, **details):
    """
    [CMD_KEY]giveemoji player emoji
    
    Give a friend an emoji.
    Why? Who knows.
    I'm sure you can have loads of game with the :cancer: emoji though!
    Also see ``[CMD_KEY]givepotato``
    
    """
    sender = details["author"]

    try:
        await give_emoji(ctx.channel, sender, receiver, emoji)
        sender.misc_stats["emojis_given"] += 1
        receiver.misc_stats["emojis"] += 1
    except util.BattleBananaException as command_error:
        raise command_error
    await awards.give_award(ctx.channel, sender, "Emoji", ":fire: __Breakdown Of Society__ :city_dusk:")
    if emoji == "🍆":
        await awards.give_award(ctx.channel, sender, "Sauce", "*Saucy*")
    if sender.misc_stats["emojis_given"] >= 100:
        if not "EmojiKing" in sender.awards:
            await awards.give_award(ctx.channel, sender, "EmojiKing", ":biohazard: **__WIPEOUT HUMANITY__** :radioactive:")


@commands.command(args_pattern='P', aliases=("potato",))
async def givepotato(ctx, receiver, **details):
    """
    [CMD_KEY]givepotato player
    
    Who doesn't like potatoes?
    """
    sender = details["author"]

    try:
        await give_emoji(ctx.channel, sender, receiver, '🥔')
        sender.misc_stats["potatoes_given"] += 1
        receiver.misc_stats["potatoes"] += 1
    except util.BattleBananaException as command_error:
        raise command_error
    await awards.give_award(ctx.channel, sender, "Potato", ":potato: Bringer Of Potatoes :potato:")
    if sender.misc_stats["potatoes_given"] >= 100:
        if not "KingTat" in sender.awards:
            await awards.give_award(ctx.channel, sender, "KingTat", ":crown: :potato: **Potato King!** :potato: :crown:")


@commands.command(args_pattern=None)
async def topdog(ctx, **_):
    """
    [CMD_KEY]topdog

    View the "top dog"
    """
    top_dog_stats = awards.get_award_stat("TopDog")
    if top_dog_stats is not None and "top_dog" in top_dog_stats:
        top_dog = players.find_player(int(top_dog_stats["top_dog"]))
        await util.reply(ctx, (":dog: The current top dog is **%s** (%s)!\n"
                                     + "They are the **%s** to earn the rank of top dog!")
                       % (top_dog, top_dog.id, util.int_to_ordinal(top_dog_stats["times_given"])))
    else:
        await util.reply(ctx, "There is not a top dog yet!")
        
        
@commands.command(args_pattern=None, aliases=["btd"])
@commands.imagecommand()
async def battletopdog(ctx, **details):
    """
    [CMD_KEY]battletopdog
    Battle the "top dog"
    """
    top_dog_stats = awards.get_award_stat("TopDog")
    if top_dog_stats is None or not "top_dog" in top_dog_stats:
        raise util.BattleBananaException(ctx.channel, "Sorry there was an error trying to find the topdog!")

    top_dog = players.find_player(int(top_dog_stats["top_dog"]))
    if top_dog is None:
        raise util.BattleBananaException(ctx.channel, "Sorry there was an error trying to find the topdog!")

    player = details["author"]
    if top_dog == player:
        raise util.BattleBananaException(ctx.channel, "Don't beat yourself up!")
    
    battle_log = battles.get_battle_log(ctx, player_one=player, player_two=top_dog)

    await imagehelper.battle_screen(ctx, player, top_dog)
    await util.reply(ctx, embed=battle_log.embed)
    if battle_log.winner is None:
        # Both players get the draw battle award
        awards.give_award(ctx.channel, player, "InconceivableBattle")
        awards.give_award(ctx.channel, top_dog, "InconceivableBattle")
    await battles.give_awards_for_battle(ctx.channel, battle_log)
        
@commands.command(args_pattern=None, aliases=["vtd"])
@commands.imagecommand()
async def viewtopdog(ctx, **_):
    """
    [CMD_KEY]viewtopdog
    See the info page of the "top dog"
    """
    top_dog_stats = awards.get_award_stat("TopDog")
    if top_dog_stats is None or not "top_dog" in top_dog_stats:
        raise util.BattleBananaException(ctx.channel, "Sorry there was an error trying to find the topdog!")

    top_dog = players.find_player(int(top_dog_stats["top_dog"]))
    if top_dog is None:
        raise util.BattleBananaException(ctx.channel, "Sorry there was an error trying to find the topdog!")

    await imagehelper.stats_screen(ctx, top_dog)


async def show_awards(ctx, top_dog, page=0):
    # Always show page 1 (0)
    if page != 0 and page * 5 >= len(top_dog.awards):
        raise util.BattleBananaException(ctx.channel, "Page not found")

    await imagehelper.awards_screen(ctx, top_dog, page,
                                    is_top_dog_sender=ctx.author.id == top_dog.id)
                       

@commands.command(args_pattern=None)
async def pandemic(ctx, **_):
    """
    [CMD_KEY]pandemic

    Tracked the passed BattleBanana pandemic.
    """
    virus_stats = awards.get_award_stat("Duerus")

    if virus_stats is None or virus_stats["times_given"] == 0:
        await util.reply(ctx, "All looks good now though a pandemic could break out any day.")
        return

    warning_symbols = {0: ":heart: - Healthy", 1: ":yellow_heart: - Worrisome", 2: ":black_heart: - Doomed"}
    thumbnails = {0: "http://i.imgur.com/NENJMOP.jpg",
                  1: "http://i.imgur.com/we6XgpG.gif",
                  2: "http://i.imgur.com/EJVYJ9C.gif"}

    total_players = dbconn.get_collection_for_object(players.Player).count()
    total_infected = virus_stats["times_given"]
    total_uninfected = total_players - total_infected
    percent_infected = (total_infected / total_players) * 100
    pandemic_level = percent_infected // 33
    pandemic_embed = discord.Embed(title=":biohazard: BattleBanana Pandemic :biohazard:", type="rich",
                                   color=gconf.DUE_COLOUR)
    # pandemic_embed.description = ("Oh my god! In the last news, infected people are invading our world!\n"
    #                               + "This is the current infection rate!")
    pandemic_embed.set_thumbnail(url=thumbnails.get(pandemic_level, thumbnails[2]))
    pandemic_embed.description = "Monitoring the spread of the __loser__ pandemic."
    pandemic_embed.add_field(name="Pandemic stats", value=("Out of a total of **%s** players:\n"
                                                           + ":biohazard: **%s** "
                                                           + ("is" if total_infected == 1 else "are") + " infected.\n"
                                                           + ":pill: **%s** "
                                                           + ("is" if total_uninfected == 1 else "are")
                                                           + " uninfected.\n\n"
                                                           + "This means **%.2g**%% of all players are infected!")
                                                          % (total_players, total_infected,
                                                             total_uninfected, percent_infected))
    pandemic_embed.add_field(name="Health level",
                             value=warning_symbols.get(pandemic_level, warning_symbols[2]))

    await util.reply(ctx, embed=pandemic_embed)

@commands.command(args_pattern=None)
async def minecraft(ctx, **_):
    """
    [CMD_KEY]minecraft

    Give you the official BattleBanana minecraft server
    """

    embed = discord.Embed(title="BananaCraft", type="rich", color=gconf.DUE_COLOUR)
    embed.add_field(name="Minecraft version:", value="1.16.1")
    embed.add_field(name="Server address:", value="mc.battlebanana.xyz")

    await util.reply(ctx, f"{emojis.QUESTER} Official BananaCraft server!", embed=embed)

@commands.command(args_pattern="C?", aliases=["tdh"])
async def topdoghistory(ctx, page=1, **_):
    """
    [CMD_KEY]topdoghistory (page)

    Display the current and the 10 previous topdogs
    """
    page -= 1
    count = dbconn.conn()["Topdogs"].find().count()

    if topdogs_per_page * page > count:
        raise util.BattleBananaException(ctx.channel, "Page not found!")

    topdogs = dbconn.conn()["Topdogs"].find({}, {'_id': 0}).sort([('date', -1)]).skip(topdogs_per_page*page).limit(topdogs_per_page)
    
    embed = discord.Embed(title="Topdog History", type="rich", color=gconf.DUE_COLOUR)
    embed.set_footer(text="Times are in UTC.")
    
    topdog = awards.get_award_stat("TopDog")
    if topdog is None or not "top_dog" in topdog:
        embed.add_field(name="Current topdog:", value=":bangbang: Failed to parse current topdog")
    else:
        topdog = players.find_player(int(topdog["top_dog"]))
        embed.add_field(name="Current topdog:", value=topdog.name)

    tdstring = ""
    for topdog in topdogs:
        player = players.find_player(topdog.get('user_id'))
        if player is not None:
            date:datetime = topdog.get('date')

            if util.is_today(date):
                tdstring += f"- **{player.name}**, today at {date.strftime('%H:%M')}\n"
            elif util.is_yesterday(date):
                tdstring += f"- **{player.name}**, yesterday at {date.strftime('%H:%M')}\n"
            else:
                tdstring += f"- **{player.name}**, at {date.strftime('%d/%m/%Y')}\n"
    
    embed.add_field(name="Previous topdogs:", value=tdstring, inline=False)

    await util.reply(ctx, embed=embed)


# import random
# @commands.command(args_pattern=None)
# async def fool(ctx, **details):
#     """
#     [CMD_KEY]fool
# 
#     Are you a fool?
#     """
#     randomnumber = random.randint(1, 100)
#     if randomnumber >= 50:
#         await util.reply(ctx, "%s is a fool!1!!11 :confused:" % (ctx.author.mention))
#     else:
#         await util.reply(ctx, "%s is not a fool!1!11!1! :smiley:" % (ctx.author.mention))
