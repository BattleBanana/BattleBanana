import time

import discord
import repoze.timeago

import generalconfig as gconf
from .. import commands, events, util, permissions
# Shorthand for emoji as I use gconf to hold emoji constants
from ..game import emojis as e
from ..game import stats, awards, discoin, translations
from ..game.configs import dueserverconfig
from ..game.stats import Stat
from ..permissions import Permission


@commands.command(permission=Permission.DISCORD_USER, args_pattern="S?", aliases=("helpme",))
async def help(ctx, *args, **details):
    """util:help:HELP"""
    player = details["author"]
    help_logo = 'https://cdn.discordapp.com/attachments/173443449863929856/275299953528537088/helo_458x458.jpg'

    help_embed = discord.Embed(title="BattleBanana's Help", type="rich", color=gconf.DUE_COLOUR)
    server_key = details["cmd_key"]
    categories = events.command_event.category_list()

    if len(args) == 1:

        help_embed.set_thumbnail(url=help_logo)
        arg = args[0].lower()
        if arg not in categories:
            chosen_command = events.get_command(arg)
            # Dumb award
            if chosen_command is None:
                alias_count = 0
                #if arg != "dumbledore":
                command_name = translations.translate(ctx, "util:help:CNOTFOUND")
                command_help = translations.translate(ctx, "util:help:CNOTFOUND2")
                #else:
                #    # Stupid award reference
                #    command_name = 'dumbledore?!?'
                #    command_help = 'Some stupid *joke?* reference to old due!!!111'
                #    help_embed.set_image(url='http://i.imgur.com/UrWhI9P.gif')
                #    await awards.give_award(ctx.channel, player, "Daddy",
                #                            "I have no memory of this award...")
            else:
                command_name = chosen_command.__name__
                alias_count = len(chosen_command.aliases)
                if chosen_command.__doc__ is not None:
                    command_help = translations.translate(ctx, chosen_command.__doc__)
                else:
                    command_help = translations.translate(ctx, "util:help:NOHELP")

            help_embed.description = translations.translate(ctx, "util:help:HELPDESC", command_name)
            help_embed.add_field(name=":gear: " + command_name, value=command_help)
            if alias_count > 0:
                help_embed.add_field(name=":performing_arts: " + ("Alias" if alias_count == 1 else "Aliases"),
                                     value=', '.join(chosen_command.aliases), inline=False)
        else:
            category = arg
            help_embed.description = translations.translate(ctx, "util:help:HELPDESC2", category)

            commands_for_all = events.command_event.command_list(
                filter=lambda command:
                command.permission in (Permission.PLAYER, Permission.DISCORD_USER) and command.category == category)
            admin_commands = events.command_event.command_list(
                filter=lambda command:
                command.permission == Permission.SERVER_ADMIN and command.category == category)
            server_op_commands = events.command_event.command_list(
                filter=lambda command:
                command.permission == Permission.REAL_SERVER_ADMIN and command.category == category)

            if len(commands_for_all) > 0:
                help_embed.add_field(name=translations.translate(ctx, "util:help:CEVERYONE"), value=', '.join(commands_for_all), inline=False)
            if len(admin_commands) > 0:
                help_embed.add_field(name=translations.translate(ctx, "util:help:CADMIN"), value=', '.join(admin_commands), inline=False)
            if len(server_op_commands) > 0:
                help_embed.add_field(name=translations.translate(ctx, "util:help:COWNER"), value=', '.join(server_op_commands), inline=False)
    else:

        help_embed.set_thumbnail(url=util.clients[0].user.avatar_url)

        help_embed.description = translations.translate(ctx, "util:help:FDESC")
        help_embed.add_field(name=':file_folder: '+translations.translate(ctx, "util:help:COMCA"), value=', '.join(categories))
        help_embed.add_field(name=e.THINKY_FONK + translations.translate(ctx, "util:help:TTIP"),
                             value=translations.translate(ctx, "util:help:TDESC"))
        help_embed.add_field(name=":link:"+translations.translate(ctx, "util:help:LLINK"), value=translations.translate(ctx, "util:help:LDESC", gconf.BOT_INVITE))
        help_embed.set_footer(
            text=translations.translate(ctx, "util:help:FOOTER"))

    await util.say(ctx.channel, embed=help_embed)


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def invite(ctx, **_):
    """util:invite:HELP"""

    invite_embed = discord.Embed(title=translations.translate(ctx, "util:invite:TITLE"), type="rich", color=gconf.DUE_COLOUR)
    invite_embed.description = translations.translate(ctx, "util:invite:DESC")
    invite_embed.add_field(name=translations.translate(ctx, "util:invite:INVITE"), value=("["+translations.translate(ctx, "util:invite:HERE")+"](%s)" % gconf.BOT_INVITE), inline=True)
    invite_embed.add_field(name=translations.translate(ctx, "util:invite:SUPPORT"), value="["+translations.translate(ctx, "util:invite:HERE")+"](https://discord.gg/P7DBDEC)", inline=True)
    await util.say(ctx.channel, embed=invite_embed)


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def donate(ctx, **_):
    """util:donate:HELP"""

    donation_embed = discord.Embed(title="Donate", type="rich", color=gconf.DUE_COLOUR)
    donation_embed.add_field(name="Patreon (Donation)", value="[Here](https://patreon.com/developeranonymous)",
                             inline=True)
    await util.say(ctx.channel, embed=donation_embed)


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def botinfo(ctx, **_):
    """util:botinfo:HELP"""

    info_embed = discord.Embed(title=translations.translate(ctx, "util:botinfo:TITLE"), type="rich", color=gconf.DUE_COLOUR)
    info_embed.description = translations.translate(ctx, "util:botinfo:DESC")
    info_embed.add_field(name=translations.translate(ctx, "util:botinfo:ORIGINAL"), value="MacDue#4453")
    info_embed.add_field(name=translations.translate(ctx, "util:botinfo:CONTINUED"), value="[DeveloperAnonymous#9830](https://battlebanana.xyz/)")
    info_embed.add_field(name=translations.translate(ctx, "util:botinfo:FRAME"),
                         value="[discord.py %s :two_hearts:](http://discordpy.readthedocs.io/en/latest/)"
                               % discord.__version__)
    info_embed.add_field(name=translations.translate(ctx, "util:botinfo:VER"), value=gconf.VERSION),
    info_embed.add_field(name=translations.translate(ctx, "util:botinfo:INVITE"), value="%s" % gconf.BOT_INVITE, inline=False)
    info_embed.add_field(name=translations.translate(ctx, "util:botinfo:NSUPPORT"),
                         value=translations.translate(ctx, "util:botinfo:DSUPPORT"))
    await util.say(ctx.channel, embed=info_embed)


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def prefix(ctx, **details):
    """util:prefix:HELP"""

    server_prefix = dueserverconfig.server_cmd_key(ctx.guild)
    await translations.say(ctx, "util:prefix:MSG", details.get("server_name_clean"), server_prefix)


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def botstats(ctx, **_):
    """util:botstats:HELP"""

    game_stats = stats.get_stats()
    stats_embed = discord.Embed(title="BattleBanana's Statistics!", type="rich", color=gconf.DUE_COLOUR)

    stats_embed.description = ("The numbers and stuff of BattleBanana right now!\n"
                               + "The **worst** Discord bot since %s, %s!"
                               % (gconf.DUE_START_DATE.strftime("%d/%m/%Y"),
                                  repoze.timeago.get_elapsed(gconf.DUE_START_DATE)))

    # General
    stats_embed.add_field(name="General",
                          value=(e.MYINFO + " **%s** images served.\n"
                                 % util.format_number_precise(game_stats[Stat.IMAGES_SERVED])
                                 + e.DISCOIN + " **Đ%s** Discoin received.\n"
                                 % util.format_number_precise(game_stats[Stat.DISCOIN_RECEIVED])))
    # Game
    stats_embed.add_field(name="Game",
                          value=(e.QUESTER + " **%s** players.\n"
                                 % util.format_number_precise(game_stats[Stat.NEW_PLAYERS_JOINED])
                                 + e.QUEST + " **%s** quests given.\n"
                                 % util.format_number_precise(game_stats[Stat.QUESTS_GIVEN])
                                 + e.FIST + " **%s** quests attempted.\n"
                                 % util.format_number_precise(game_stats[Stat.QUESTS_ATTEMPTED])
                                 + e.LEVEL_UP + " **%s** level ups.\n"
                                 % util.format_number_precise(game_stats[Stat.PLAYERS_LEVELED])
                                 + e.BBT + " **%s** awarded.\n"
                                 % util.format_money(game_stats[Stat.MONEY_CREATED])
                                 + e.BBT_WITH_WINGS + " **%s** transferred between players."
                                 % util.format_money(game_stats[Stat.MONEY_TRANSFERRED])),
                          inline=False)
    # Sharding
    client = util.clients[0]
    current_shard = util.get_shard_index(ctx.guild.id)
    stats_embed.add_field(name="Shard",
                          value=("You're connected to shard **%d/%d** (that is named %s).\n"
                                 % (current_shard + 1, client.shard_count, gconf.shard_names[current_shard])
                                 + "Current uptime is %s."
                                 % util.display_time(time.time() - client.start_time, granularity=4)),
                          inline=False)

    await util.say(ctx.channel, embed=stats_embed)


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def servers(ctx, **_):
    """util:servers:HELP"""

    server_count = util.get_server_count()
    await translations.say(ctx, "util:servers:MSG", server_count)


@commands.command(permission=Permission.REAL_SERVER_ADMIN, args_pattern="S", aliases=("sl",))
async def setlanguage(ctx, new_lan, **details):
    """util:setlanguage:HELP"""

    if util.filter_string(new_lan) != new_lan:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "util:setlanguage:ERROR"))

    if str(new_lan) in ("en", "fr"):
        dueserverconfig.set_language(ctx.guild, new_lan)
        await translations.say(ctx, "util:setlanguage:SUCCESS", ctx.guild.name, new_lan)
    else:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "util:setlanguage:ERROR"))


@commands.command(permission=Permission.REAL_SERVER_ADMIN, args_pattern=None)
async def languages(ctx, **_):
    """util:languages:HELP"""

    lan_embed = discord.Embed(title="BattleBanana's Localization!", type="rich", color=gconf.DUE_COLOUR)
    lan_embed.description = "en - English\n fr - Français"

    await util.say(ctx.channel, embed=lan_embed)



@commands.command(permission=Permission.SERVER_ADMIN, args_pattern="S", aliases=("setprefix",))
async def setcmdkey(ctx, new_key, **details):
    """util:setcmdkey:HELP"""
    if util.filter_string(new_key) != new_key:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "util:setcmdkey:INVALIDKEY"))

    if len(new_key) in (1, 2):
        dueserverconfig.server_cmd_key(ctx.guild, new_key)
        await translations.say(ctx, "util:setcmdkey:SUCCESS", ctx.guild.name, new_key)
    else:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "util:setcmdkey:INVALIDCHARS"))


@commands.command(permission=Permission.SERVER_ADMIN, args_pattern="S?")
async def shutup(ctx, *args, **details):
    """util:shutup:HELP"""

    if len(args) == 0:
        mute_success = dueserverconfig.mute_channel(ctx.channel)
        if mute_success:
            await util.say(ctx.channel, (":mute: I won't send any alerts in this channel!\n"
                                         + "If you meant to disable commands too do ``" + details[
                                             "cmd_key"] + "shutup all``."))
        else:
            await util.say(ctx.channel, (":mute: I've already been set not to send alerts in this channel!\n"
                                         + "If you want to disable commands too do ``" + details["cmd_key"]
                                         + "shutup all``.\n"
                                         + "To unmute me do ``" + details["cmd_key"] + "unshutup``."))
    else:
        mute_level = args[0].lower()
        if mute_level == "all":
            mute_success = dueserverconfig.mute_channel(ctx.channel, mute_all=True)
            if mute_success:
                await util.say(ctx.channel, ":mute: Disabled all commands in this channel for non-admins!")
            else:
                await util.say(ctx.channel, (":mute: Already mute af in this channel!.\n"
                                             + "To allow commands & alerts again do ``" + details[
                                                 "cmd_key"] + "unshutup``."))
        else:
            await util.say(ctx.channel, ":thinking: If you wanted to mute all the command is ``" + details[
                "cmd_key"] + "shutup all``.")


@commands.command(permission=Permission.REAL_SERVER_ADMIN, args_pattern="S?")
@commands.require_cnf(warning="The bot will leave your guild and __**everything**__ will be reset!")
async def leave(ctx, **_):
    """
    [CMD_KEY]leave
    
    Makes BattleBanana leave your guild cleanly.
    This will delete all quests & weapons created
    on your guild.
    
    This command can only be run by real guild admins
    (you must have manage guild permissions).
    
    """

    bye_embed = discord.Embed(title="Goodbye!", color=gconf.DUE_COLOUR)
    bye_embed.set_image(url="http://i.imgur.com/N65P9gL.gif")
    await util.say(ctx.channel, embed=bye_embed)
    try:
        await ctx.guild.leave()
    except:
        raise util.BattleBananaException(ctx.channel, "Could not leave guild!")


@commands.command(permission=Permission.SERVER_ADMIN, args_pattern=None)
async def unshutup(ctx, **_):
    """
    [CMD_KEY]unshutup

    Reverts ``[CMD_KEY]shutup`` or ``[CMD_KEY]shutup all``
    (allowing BattleBanana to give alerts and be used again).

    """
    if dueserverconfig.unmute_channel(ctx.channel):
        await util.say(ctx.channel,
                       ":speaker: Okay! I'll once more send alerts and listen for commands in this channel!")
    else:
        await util.say(ctx.channel, ":thinking: Okay... I'm unmuted but I was not muted anyway.")


@commands.command(permission=Permission.SERVER_ADMIN, args_pattern="S*")
async def whitelist(ctx, *args, **_):
    """
    [CMD_KEY]whitelist
    
    Choose what BattleBanana commands you want to allow in a channel.
    E.g. ``[CMD_KEY]whitelist help battle shop myinfo info``
    
    Normal users will not be able to use any other commands than the ones you
    choose.
    The whitelist does not effect guild admins.
    
    To reset the whitelist run the command with no arguments.

    Note: Whitelisting a command like !info will also whitelist !myinfo
    (since !info is mapped to !myinfo)
    """

    if len(args) > 0:
        due_commands = events.command_event.command_list(aliases=True)
        whitelisted_commands = set(commands.replace_aliases([command.lower() for command in args]))
        if whitelisted_commands.issubset(due_commands):
            dueserverconfig.set_command_whitelist(ctx.channel, list(whitelisted_commands))
            await util.say(ctx.channel, (":notepad_spiral: Whitelist in this channel set to the following commands: ``"
                                         + ', '.join(whitelisted_commands) + "``"))
        else:
            incorrect_commands = whitelisted_commands.difference(due_commands)
            await util.say(ctx.channel, (":confounded: Cannot set whitelist! The following commands don't exist: ``"
                                         + ', '.join(incorrect_commands) + "``"))
    else:
        dueserverconfig.set_command_whitelist(ctx.channel, [])
        await util.say(ctx.channel, ":pencil: Command whitelist set back to all commands.")


@commands.command(permission=Permission.SERVER_ADMIN, args_pattern="S*")
async def blacklist(ctx, *args, **_):
    """
    [CMD_KEY]blacklist
    
    Choose what BattleBanana commands you want to ban in a channel.
    E.g. ``[CMD_KEY]blacklist acceptquest battleme sell``
    
    Normal users will only be able to use commands not in the blacklist.
    The blacklist does not effect guild admins.
    
    To reset the blacklist run the command with no arguments.
    
    The blacklist is not independent from the whitelist.

    Note: Blacklisting a command like !info will also blacklist !myinfo
    (since !info is mapped to !myinfo)
    """

    if len(args) > 0:
        due_commands = events.command_event.command_list(aliases=True)
        blacklisted_commands = set(commands.replace_aliases([command.lower() for command in args]))
        if blacklisted_commands.issubset(due_commands):
            whitelisted_commands = list(set(due_commands).difference(blacklisted_commands))
            whitelisted_commands.append("is_blacklist")
            dueserverconfig.set_command_whitelist(ctx.channel, whitelisted_commands)
            await util.say(ctx.channel, (":notepad_spiral: Blacklist in this channel set to the following commands: ``"
                                         + ', '.join(blacklisted_commands) + "``"))
        else:
            incorrect_commands = blacklisted_commands.difference(due_commands)
            await util.say(ctx.channel, (":confounded: Cannot set blacklist! The following commands don't exist: ``"
                                         + ', '.join(incorrect_commands) + "``"))
    else:
        dueserverconfig.set_command_whitelist(ctx.channel, [])
        await util.say(ctx.channel, ":pencil: Command blacklist removed.")


@commands.command(permission=Permission.REAL_SERVER_ADMIN, args_pattern=None)
async def setuproles(ctx, **_):
    """
    [CMD_KEY]setuproles
    
    Creates any discord roles BattleBanana needs. These will have been made when
    BattleBanana joined your guild but if you deleted any & need them you'll 
    want to run this command.
    
    """
    roles_made = await util.set_up_roles(ctx.guild)
    roles_count = len(roles_made)
    if roles_count > 0:
        result = ":white_check_mark: Created **%d %s**!\n" % (roles_count, util.s_suffix("role", roles_count))
        for role in roles_made:
            result += "→ ``%s``\n" % role["name"]
        await util.say(ctx.channel, result)
    else:
        await util.say(ctx.channel, "No roles need to be created!")


async def optout_is_topdog_check(channel, player):
    topdog = player.is_top_dog()
    if topdog:
        await util.say(channel, (":dog: You cannot opt out while you're top dog!\n"
                                 + "Pass on the title before you leave us!"))
    return topdog


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def optout(ctx, **details):
    """
    [CMD_KEY]optout

    Optout of BattleBanana.

    When you opt out:
        You don't get quests or exp.
        Other players can't use you in commands.
        You lose access to all "game" commands.

    Guild admins (that opt out) still have access to admin commands.

    (This applies to all servers with BattleBanana)
    """

    player = details["author"]
    if player.is_playing():
        current_permission = permissions.get_special_permission(ctx.author)
        if await optout_is_topdog_check(ctx.channel, player):
            return
        if current_permission >= Permission.BANANA_MOD:
            raise util.BattleBananaException(ctx.channel,
                                             "You cannot optout everywhere and stay a BattleBanana mod or admin!")
        permissions.give_permission(ctx.author, Permission.DISCORD_USER)
        await util.say(ctx.channel, (":ok_hand: You've opted out of BattleBanana everywhere.\n"
                                     + "You won't get exp, quests, and other players can't use you in commands."))
    else:
        await util.say(ctx.channel, ("You've already opted out everywhere!\n"
                                     + "You can join the fun again with ``%soptin``." % details["cmd_key"]))


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def optin(ctx, **details):
    """
    [CMD_KEY]optin

    Optin to BattleBanana.

    (This applies to all servers with BattleBanana)
    """

    player = details["author"]
    local_optout = not player.is_playing(ctx.guild, local=True)
    # Already playing
    if player.is_playing():
        if not local_optout:
            await util.say(ctx.channel, "You've already opted in everywhere!")
        else:
            await util.say(ctx.channel, ("You've only opted out on this guild!\n"
                                         + "To optin here do ``%soptinhere``" % details["cmd_key"]))
    else:
        permissions.give_permission(ctx.author, Permission.PLAYER)
        await util.say(ctx.channel, ("You've opted in everywhere"
                                     + (" (does not override your guild level optout)" * local_optout) + "!\n"
                                     + "Glad to have you back."))


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def optouthere(ctx, **details):
    """
    [CMD_KEY]optouthere

    Optout of BattleBanana on the guild you run the command.
    This has the same effect as [CMD_KEY]optout but is local.
    """

    player = details["author"]

    if not player.is_playing():
        await util.say(ctx.channel, "You've already opted out everywhere!")
        return

    if player.is_playing(ctx.guild, local=True):
        optout_role = util.get_role_by_name(ctx.guild, gconf.OPTOUT_ROLE)
        if optout_role is None:
            await util.say(ctx.channel, ("There is no optout role on this guild!\n"
                                         + "Ask an admin to run ``%ssetuproles``" % details["cmd_key"]))
        else:
            if await optout_is_topdog_check(ctx.channel, player):
                return
            await ctx.author.add_roles(optout_role)
            await util.say(ctx.channel, (":ok_hand: You've opted out of BattleBanana on this guild!\n"
                                         + "You won't get exp, quests or be able to use commands here."))
    else:
        await util.say(ctx.channel, ("You've already opted out on this sever!\n"
                                     + "Join the fun over here do ``%soptinhere``" % details["cmd_key"]))


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def optinhere(ctx, **details):
    """
    [CMD_KEY]optinhere

    Optin to BattleBanana on a guild.
    """

    player = details["author"]
    globally_opted_out = not player.is_playing()

    optout_role = util.get_role_by_name(ctx.guild, gconf.OPTOUT_ROLE)
    if optout_role is not None and not player.is_playing(ctx.guild, local=True):
        await ctx.author.remove_roles(optout_role)
        await util.say(ctx.channel, ("You've opted in on this guild!\n"
                                     + ("However this is overridden by your global optout.\n"
                                        + "To optin everywhere to ``%soptin``" % details["cmd_key"])
                                     * globally_opted_out))
    else:
        if globally_opted_out:
            await util.say(ctx.channel, ("You've opted out of BattleBanana everywhere!\n"
                                         + "To use BattleBanana do ``%soptin``" % details["cmd_key"]))
        else:
            await util.say(ctx.channel, "You've not opted out on this guild.")


@commands.command(args_pattern=None)
async def currencies(ctx, **details):
    """
    [CMD_KEY]currencies
    
    Display every currencies currently available on Discoin
    """

    embed = discord.Embed(title=e.DISCOIN + " Current currencies!", type="rich", color=gconf.DUE_COLOUR)
    for id in discoin.CODES:
        currency = discoin.CODES[id]
        embed.add_field(name=id, value=currency['name'], inline=False)

    if len(embed.fields) == 0:
        embed.add_field(name="An error occured!", value="There was an error retrieving Discoin's currencies.")
    embed.set_footer(text="Visit https://dash.discoin.zws.im/#/currencies for exchange rate.")

    await util.say(ctx.channel, embed=embed)


@commands.ratelimit(cooldown=300, error="util:exchange:RATELIMIT", save=True)
@commands.command(args_pattern="CS", aliases=["convert"])
async def exchange(ctx, amount, currency, **details):
    """util:exchange:HELP"""

    player = details["author"]
    currency = currency.upper()

    if currency == discoin.CURRENCY_CODE:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "util:exchange:SAMECURRENCY", discoin.CURRENCY_CODE, discoin.CURRENCY_CODE))
    if not currency in discoin.CODES:
        raise util.BattleBananaException(ctx.channel,
                                         "Not a valid currency! Use `%scurrencies` to know which currency is available." %
                                         details['cmd_key'])
    if amount > discoin.MAX_TRANSACTION:
        raise util.BattleBananaException(ctx.channel,
                                         "The amount you try to exchange exceeds the maximum %s transfer limit of %s."
                                         % (discoin.CURRENCY_CODE, discoin.MAX_TRANSACTION))

    amount = int(amount)
    if player.money - amount < 0:
        await util.say(ctx.channel, "You do not have **%s**!\n"
                       % util.format_number(amount, full_precision=True, money=True)
                       + "The maximum you can exchange is **%s**"
                       % util.format_number(player.money, full_precision=True, money=True))
        return

    try:
        response = await discoin.make_transaction(player.id, amount, currency)
    except Exception as discoin_error:
        util.logger.error("Discoin exchange failed %s", discoin_error)
        raise util.BattleBananaException(ctx.channel, "Something went wrong at Discoin!")

    if response.get('statusCode'):
        code = response.get("statusCode")
        if code >= 500:
            raise util.BattleBananaException(ctx.channel,
                                             "Something went wrong at Discoin! %s: %s" % (code, response['error']))
        elif 400 <= code < 500:
            raise util.BattleBananaException(ctx.channel, "Something went wrong! %s: %s" % (code, response['error']))

    await awards.give_award(ctx.channel, player, "Discoin")
    player.money -= amount
    player.save()

    transaction = response
    receipt = discoin.DISCOINDASH + "/" + transaction['id'] + "/show"

    exchange_embed = discord.Embed(title=e.DISCOIN + " Exchange complete!", type="rich", color=gconf.DUE_COLOUR)
    exchange_embed.add_field(name=f"Exchange amount ({discoin.CURRENCY_CODE}):",
                             value=util.format_number(amount, money=True, full_precision=True))
    exchange_embed.add_field(name="Result amount (%s):" % currency,
                             value="$" + util.format_number_precise(transaction['payout']))
    exchange_embed.add_field(name="Receipt:", value=receipt, inline=False)
    exchange_embed.set_footer(text="Keep the receipt for if something goes wrong!")

    await util.say(ctx.channel, embed=exchange_embed)

    to = transaction.get("to")
    toID = to.get("id")
    payout = float(transaction.get('payout'))

    logs_embed = discord.Embed(title="Discion Transaction",
                               description="Receipt ID: [%s](%s)" % (transaction["id"], receipt),
                               type="rich", colour=gconf.DUE_COLOUR)
    logs_embed.add_field(name="User:", value=f"{player.user_id}")
    logs_embed.add_field(name="Exchange", value="%s %s => %.2f %s" % (amount, discoin.CURRENCY_CODE, payout, toID),
                         inline=False)

    await util.say(gconf.discoin_channel, embed=logs_embed)


@commands.command(args_pattern="S?", permission=Permission.BANANA_ADMIN)
async def status(ctx, message=None, **details):
    """
    If message is none the status will be reset to the default one.

    This sets the status of all the shards to the one specified.
    """

    client: discord.AutoShardedClient = util.clients[0]
    if message is None:
        count = client.shard_count
        for shardID in range(0, count):
            game = discord.Activity(name="battlebanana.xyz | shard %d/%d" % (shardID, count),
                                    type=discord.ActivityType.watching)
            await client.change_presence(activity=game, afk=False, shard_id=shardID)
    else:
        await client.change_presence(activity=discord.Activity(name=message, type=discord.ActivityType.watching),
                                     afk=False)

    await util.say(ctx.channel, "All done!")
