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
                    command_help = translations.translate_help(ctx, chosen_command.__doc__)
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
        help_embed.add_field(name=":link:"+translations.translate(ctx, "util:help:LLINK"), value=translations.translate(ctx, "util:help:LDESC"))
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

    stats_embed.description = translations.translate(ctx, "util:botstats:DESC", gconf.DUE_START_DATE.strftime("%d/%m/%Y") ,repoze.timeago.get_elapsed(gconf.DUE_START_DATE))

    # General
    stats_embed.add_field(name=translations.translate(ctx, "util:botstats:GENERAL"),
                          value=(e.MYINFO + translations.translate(ctx, "util:botstats:IMAGE", util.format_number_precise(game_stats[Stat.IMAGES_SERVED]))
                                 + e.DISCOIN + translations.translate(ctx, "util:botstats:DISCOIN", util.format_number_precise(game_stats[Stat.DISCOIN_RECEIVED]))))
    # Game
    stats_embed.add_field(name=translations.translate(ctx, "util:botstats:GAME"),
                          value=(e.QUESTER + translations.translate(ctx, "util:botstats:PLAYERS", util.format_number_precise(game_stats[Stat.NEW_PLAYERS_JOINED]))
                                 + e.QUEST + translations.translate(ctx, "util:botstats:QUESTS", util.format_number_precise(game_stats[Stat.QUESTS_GIVEN]))
                                 + e.FIST + translations.translate(ctx, "util:botstats:QUESTSGIVEN", util.format_number_precise(game_stats[Stat.QUESTS_ATTEMPTED]))
                                 + e.LEVEL_UP + translations.translate(ctx, "util:botstats:LEVELS", util.format_number_precise(game_stats[Stat.PLAYERS_LEVELED]))
                                 + e.BBT + translations.translate(ctx, "util:botstats:BBTS", util.format_money(game_stats[Stat.MONEY_CREATED]))
                                 + e.BBT_WITH_WINGS + translations.translate(ctx, "util:botstats:BBTSTRANSFERED", util.format_money(game_stats[Stat.MONEY_TRANSFERRED]))),
                          inline=False)
    # Sharding
    client = util.clients[0]
    current_shard = util.get_shard_index(ctx.guild.id)
    stats_embed.add_field(name=translations.translate(ctx, "util:botstats:SHARD"),
                          value=(translations.translate(ctx, "util:botstats:NAME", current_shard + 1, client.shard_count, gconf.shard_names[current_shard])
                                 + translations.translate(ctx, "util:botstats:UPTIME", util.display_time(time.time() - client.start_time, granularity=4))),
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

    if str(new_lan) in ("en", "es", "fr"):
        dueserverconfig.set_language(ctx.guild, new_lan)
        await translations.say(ctx, "util:setlanguage:SUCCESS", ctx.guild.name, new_lan)
    else:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "util:setlanguage:ERROR"))


@commands.command(permission=Permission.REAL_SERVER_ADMIN, args_pattern=None)
async def languages(ctx, **_):
    """util:languages:HELP"""

    lan_embed = discord.Embed(title="BattleBanana's Localization!", type="rich", color=gconf.DUE_COLOUR)
    lan_embed.description = "en - English\n es - Español\n fr - Français"

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
            await translations.say(ctx, "util:shutup:MUTESUCCESS")
        else:
            await translations.say(ctx, "util:shutup:MUTEERROR")
    else:
        mute_level = args[0].lower()
        if mute_level == "all":
            mute_success = dueserverconfig.mute_channel(ctx.channel, mute_all=True)
            if mute_success:
                await translations.say(ctx, "util:shutup:MUTEALLSUCCESS")
            else:
                await translations.say(ctx, "util:shutup:MUTEALLERROR")
        else:
            await translations.say(ctx, "util:shutup:ERROR")


@commands.command(permission=Permission.REAL_SERVER_ADMIN, args_pattern="S?")
@commands.require_cnf(warning="util:leave:CNF")
async def leave(ctx, **_):
    """util:leave:HELP"""

    bye_embed = discord.Embed(title=translations.translate(ctx, "util:leave:BYE"), color=gconf.DUE_COLOUR)
    bye_embed.set_image(url="http://i.imgur.com/N65P9gL.gif")
    await util.say(ctx.channel, embed=bye_embed)
    try:
        await ctx.guild.leave()
    except:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "util:leave:ERROR"))


@commands.command(permission=Permission.SERVER_ADMIN, args_pattern=None)
async def unshutup(ctx, **_):
    """util:unshutup:HELP"""
    if dueserverconfig.unmute_channel(ctx.channel):
        await translations.say(ctx, "util:unshutup:SUCCESS")
    else:
        await translations.say(ctx, "util:unshutup:NOTMUTED")


@commands.command(permission=Permission.SERVER_ADMIN, args_pattern="S*")
async def whitelist(ctx, *args, **_):
    """util:whitelist:HELP"""

    if len(args) > 0:
        due_commands = events.command_event.command_list(aliases=True)
        whitelisted_commands = set(commands.replace_aliases([command.lower() for command in args]))
        if whitelisted_commands.issubset(due_commands):
            dueserverconfig.set_command_whitelist(ctx.channel, list(whitelisted_commands))
            await translations.say(ctx, "util:whitelist:SUCCESS", ', '.join(whitelisted_commands))
        else:
            incorrect_commands = whitelisted_commands.difference(due_commands)
            await translations.say(ctx, "util:whitelist:ERROR", ', '.join(incorrect_commands))
    else:
        dueserverconfig.set_command_whitelist(ctx.channel, [])
        await translations.say(ctx, "util:whitelist:RESET")


@commands.command(permission=Permission.SERVER_ADMIN, args_pattern="S*")
async def blacklist(ctx, *args, **_):
    """util:blacklist:HELP"""

    if len(args) > 0:
        due_commands = events.command_event.command_list(aliases=True)
        blacklisted_commands = set(commands.replace_aliases([command.lower() for command in args]))
        if blacklisted_commands.issubset(due_commands):
            whitelisted_commands = list(set(due_commands).difference(blacklisted_commands))
            whitelisted_commands.append("is_blacklist")
            dueserverconfig.set_command_whitelist(ctx.channel, whitelisted_commands)
            await translations.say(ctx, "util:blacklist:SUCCESS", ', '.join(blacklisted_commands))
        else:
            incorrect_commands = blacklisted_commands.difference(due_commands)
            await translations.say(ctx, "util:blacklist:ERROR", ', '.join(incorrect_commands))
    else:
        dueserverconfig.set_command_whitelist(ctx.channel, [])
        await translations.say(ctx, "util:blacklist:RESET")


@commands.command(permission=Permission.REAL_SERVER_ADMIN, args_pattern=None)
async def setuproles(ctx, **_):
    """util:setuproles:HELP"""
    roles_made = await util.set_up_roles(ctx.guild)
    roles_count = len(roles_made)
    if roles_count > 0:
        result = translations.translate(ctx, "util:setuproles:CREATED", roles_count, util.s_suffix("role", roles_count))
        for role in roles_made:
            result += "→ ``%s``\n" % role["name"]
        await util.say(ctx.channel, result)
    else:
        await translations.say(ctx, "util:setuproles:NONEW")


async def optout_is_topdog_check(ctx, player):
    topdog = player.is_top_dog()
    if topdog:
        await translations.say(ctx, "util:misc:TOPDOGCHECK")
    return topdog


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def optout(ctx, **details):
    """util:optout:HELP"""

    player = details["author"]
    if player.is_playing():
        current_permission = permissions.get_special_permission(ctx.author)
        if await optout_is_topdog_check(ctx, player):
            return
        if current_permission >= Permission.BANANA_MOD:
            raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "util:optout:STAFFMEMBER"))
        permissions.give_permission(ctx.author, Permission.DISCORD_USER)
        await util.say(ctx.channel, translations.translate(ctx, "util:optout:SUCCESS"))
    else:
        await util.say(ctx.channel, translations.translate(ctx, "util:optout:ALREADYOPTOUT"))


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def optin(ctx, **details):
    """util:optin:HELP"""

    player = details["author"]
    local_optout = not player.is_playing(ctx.guild, local=True)
    # Already playing
    if player.is_playing():
        if not local_optout:
            await translations.translate(ctx, "util:optin:ALREADYOPTOUT")
        else:
            await translations.say(ctx, "util:optin:OPTOUTGUILD")
    else:
        permissions.give_permission(ctx.author, Permission.PLAYER)
        await translations.say(ctx, "util:optin:OPTOUTALL")


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def optouthere(ctx, **details):
    """util:optouthere:HELP"""

    player = details["author"]

    if not player.is_playing():
        await translations.say(ctx, "util:optouthere:ALREADYOPTOUT")
        return

    if player.is_playing(ctx.guild, local=True):
        optout_role = util.get_role_by_name(ctx.guild, gconf.OPTOUT_ROLE)
        if optout_role is None:
            await translations.say(ctx, "util:optouthere:NOROLE")
        else:
            if await optout_is_topdog_check(ctx, player):
                return
            await ctx.author.add_roles(optout_role)
            await translations.say(ctx, "util:optouthere:SUCCESS")
    else:
        await translations.say(ctx, "util:optouthere:ALREADY")


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def optinhere(ctx, **details):
    """util:optinhere:HELP"""

    player = details["author"]
    globally_opted_out = not player.is_playing()

    optout_role = util.get_role_by_name(ctx.guild, gconf.OPTOUT_ROLE)
    if optout_role is not None and not player.is_playing(ctx.guild, local=True):
        await ctx.author.remove_roles(optout_role)
        await translations.say(ctx, "util:optinhere:SUCCESS")
    else:
        if globally_opted_out:
            await translations.say(ctx, "util:optinhere:GLOBAL")
        else:
            await translations.say(ctx, "util:optinhere:NOTOPTOUT")


@commands.command(args_pattern=None)
async def currencies(ctx, **details):
    """util:currencies:HELP"""

    link = "https://dash.discoin.zws.im/#/currencies"
    embed = discord.Embed(title=e.DISCOIN + translations.translate(ctx, "util:currencies:TITLE"), type="rich", color=gconf.DUE_COLOUR)
    for id in discoin.CODES:
        currency = discoin.CODES[id]
        embed.add_field(name=id, value=currency['name'], inline=False)

    if len(embed.fields) == 0:
        embed.add_field(name=translations.translate(ctx, "util:currencies:NERROR"), value=translations.translate(ctx, "util:currencies:VERROR"))
    embed.set_footer(text=translations.translate(ctx, "util:currencies:FOOTER", link))

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
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "util:exchange:BADCURRENCY"))
    if amount > discoin.MAX_TRANSACTION:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "util:exchange:BREAKSLIMIT", discoin.CURRENCY_CODE, discoin.MAX_TRANSACTION))

    amount = int(amount)
    if player.money - amount < 0:
        await translations.say(ctx, "util:exchange:CANTAFFORD", util.format_number(amount, full_precision=True, money=True), util.format_number(player.money, full_precision=True, money=True))
        return

    try:
        response = await discoin.make_transaction(player.id, amount, currency)
    except Exception as discoin_error:
        util.logger.error("Discoin exchange failed %s", discoin_error)
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "util:exchange:ERRORDISCOIN"))

    if response.get('statusCode'):
        code = response.get("statusCode")
        if code >= 500:
            raise util.BattleBananaException(ctx.channel,  (translations.translate(ctx, "util:exchange:ERRORDISCOIN")+"%s: %s" % (code, response['error'])))
        elif 400 <= code < 500:
            raise util.BattleBananaException(ctx.channel, (translations.translate(ctx, "util:exchange:ERRORBOT")+"%s: %s" % (code, response['error'])))

    await awards.give_award(ctx.channel, player, "Discoin")
    player.money -= amount
    player.save()

    transaction = response
    receipt = discoin.DISCOINDASH + "/" + transaction['id'] + "/show"

    exchange_embed = discord.Embed(title=e.DISCOIN + translations.translate(ctx, "util:exchange:TITLE"), type="rich", color=gconf.DUE_COLOUR)
    exchange_embed.add_field(name=translations.translate(ctx, "util:exchange:EXCHANGE", discoin.CURRENCY_CODE),
                             value=util.format_number(amount, money=True, full_precision=True))
    exchange_embed.add_field(name=translations.translate(ctx, "util:exchange:RESULT", currency),
                             value="$" + util.format_number_precise(transaction['payout']))
    exchange_embed.add_field(name=translations.translate(ctx, "util:exchange:RECEIPT"), value=receipt, inline=False)
    exchange_embed.set_footer(text=translations.translate(ctx, "util:exchange:FOOTER"))

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


@commands.command(args_pattern="S?", hidden=True, permission=Permission.BANANA_ADMIN)
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
