import time
import asyncio
import discord
import repoze.timeago
import json
from itertools import chain

import generalconfig as gconf
from .. import commands, events, util, permissions
# Shorthand for emoji as I use gconf to hold emoji constants
from ..game import emojis as e
from ..game import stats, awards, discoin, players, translations
from ..game.configs import dueserverconfig
from ..game.stats import Stat
from ..permissions import Permission


@commands.command(permission=Permission.DISCORD_USER, args_pattern="S?", aliases=("helpme",))
async def help(ctx, *args, **details):
    """util:help:Help"""
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
                command_name = translations.translate(ctx, "util:help:CNotFound")
                command_help = translations.translate(ctx, "util:help:CNotFound2")
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
                    command_help = translations.translate(ctx, "util:help:NoHelp")

            help_embed.description = translations.translate(ctx, "util:help:HelpDesc", command_name)
            help_embed.add_field(name=":gear: " + command_name, value=command_help)
            if alias_count > 0:
                help_embed.add_field(name=":performing_arts: " + ("Alias" if alias_count == 1 else "Aliases"),
                                     value=', '.join(chosen_command.aliases), inline=False)
        else:
            category = arg
            help_embed.description = translations.translate(ctx, "util:help:HelpDesc2", category)

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
                help_embed.add_field(name=translations.translate(ctx, "util:help:CEveryone"), value=', '.join(commands_for_all), inline=False)
            if len(admin_commands) > 0:
                help_embed.add_field(name=translations.translate(ctx, "util:help:CAdmin"), value=', '.join(admin_commands), inline=False)
            if len(server_op_commands) > 0:
                help_embed.add_field(name=translations.translate(ctx, "util:help:COwner"), value=', '.join(server_op_commands), inline=False)
    else:

        help_embed.set_thumbnail(url=util.clients[0].user.avatar_url)

        help_embed.description = translations.translate(ctx, "util:help:FDesc")
        help_embed.add_field(name=':file_folder: '+translations.translate(ctx, "util:help:ComCa"), value=', '.join(categories))
        help_embed.add_field(name=e.THINKY_FONK + translations.translate(ctx, "util:help:TTip"),
                             value=translations.translate(ctx, "util:help:TDesc"))
        help_embed.add_field(name=":link:"+translations.translate(ctx, "util:help:LLink"), value=translations.translate(ctx, "util:help:LDesc"))
        help_embed.set_footer(
            text=translations.translate(ctx, "util:help:Footer"))

    await util.reply(ctx, embed=help_embed)


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def invite(ctx, **_):
    """util:invite:Help"""

    invite_embed = discord.Embed(title=translations.translate(ctx, "util:invite:Title"), type="rich", color=gconf.DUE_COLOUR)
    invite_embed.description = translations.translate(ctx, "util:invite:Desc")
    invite_embed.add_field(name=translations.translate(ctx, "util:invite:Invite"), value=("["+translations.translate(ctx, "other:singlewords:Here")+"](%s)" % gconf.BOT_INVITE), inline=True)
    invite_embed.add_field(name=translations.translate(ctx, "util:invite:Support"), value="["+translations.translate(ctx, "other:singlewords:Here")+"](https://discord.gg/P7DBDEC)", inline=True)
    await util.reply(ctx, embed=invite_embed)


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def donate(ctx, **_):
    """util:donate:Help"""

    donation_embed = discord.Embed(title="Donate", type="rich", color=gconf.DUE_COLOUR)
    donation_embed.add_field(name="Patreon (Donation)", value="[Here](https://patreon.com/developeranonymous)",
                             inline=True)
    await util.reply(ctx, embed=donation_embed)


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def botinfo(ctx, **_):
    """util:botinfo:Help"""

    info_embed = discord.Embed(title=translations.translate(ctx, "util:botinfo:Title"), type="rich", color=gconf.DUE_COLOUR)
    info_embed.description = translations.translate(ctx, "util:botinfo:Desc")
    info_embed.add_field(name=translations.translate(ctx, "util:botinfo:Original"), value="MacDue#4453")
    info_embed.add_field(name=translations.translate(ctx, "util:botinfo:Continued"), value="[DeveloperAnonymous#9830](https://battlebanana.xyz/)")
    info_embed.add_field(name=translations.translate(ctx, "util:botinfo:Frame"),
                         value="[discord.py %s :two_hearts:](http://discordpy.readthedocs.io/en/latest/)"
                               % discord.__version__)
    info_embed.add_field(name=translations.translate(ctx, "util:botinfo:Ver"), value=gconf.VERSION),
    info_embed.add_field(name=translations.translate(ctx, "util:botinfo:Invite"), value="%s" % gconf.BOT_INVITE, inline=False)
    info_embed.add_field(name=translations.translate(ctx, "util:botinfo:NSupport"),
                         value=translations.translate(ctx, "util:botinfo:DSupport"))
    await util.reply(ctx, embed=info_embed)


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def prefix(ctx, **details):
    """util:prefix:Help"""

    server_prefix = dueserverconfig.server_cmd_key(ctx.guild)
    await translations.say(ctx, "util:prefix:Response", details.get("server_name_clean"), server_prefix)


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def botstats(ctx, **_):
    """util:botstats:Help"""

    game_stats = stats.get_stats()
    stats_embed = discord.Embed(title="BattleBanana's Statistics!", type="rich", color=gconf.DUE_COLOUR)

    stats_embed.description = translations.translate(ctx, "util:botstats:Desc", gconf.DUE_START_DATE.strftime("%d/%m/%Y") ,repoze.timeago.get_elapsed(gconf.DUE_START_DATE))

    # General
    stats_embed.add_field(name=translations.translate(ctx, "util:botstats:General"),
                          value=(e.MYINFO + translations.translate(ctx, "util:botstats:Images", util.format_number_precise(game_stats[Stat.IMAGES_SERVED]))
                                 + e.DISCOIN + translations.translate(ctx, "util:botstats:Discoin", util.format_number_precise(game_stats[Stat.DISCOIN_RECEIVED]))))
    # Game
    stats_embed.add_field(name=translations.translate(ctx, "util:botstats:Game"),
                          value=(e.QUESTER + translations.translate(ctx, "util:botstats:Players", util.format_number_precise(game_stats[Stat.NEW_PLAYERS_JOINED]))
                                 + e.QUEST + translations.translate(ctx, "util:botstats:Quests", util.format_number_precise(game_stats[Stat.QUESTS_GIVEN]))
                                 + e.FIST + translations.translate(ctx, "util:botstats:QuestsGiven", util.format_number_precise(game_stats[Stat.QUESTS_ATTEMPTED]))
                                 + e.LEVEL_UP + translations.translate(ctx, "util:botstats:Levels", util.format_number_precise(game_stats[Stat.PLAYERS_LEVELED]))
                                 + e.BBT + translations.translate(ctx, "util:botstats:Currency", util.format_money(game_stats[Stat.MONEY_CREATED]))
                                 + e.BBT_WITH_WINGS + translations.translate(ctx, "util:botstats:CurrencyTransfer", util.format_money(game_stats[Stat.MONEY_TRANSFERRED]))),
                          inline=False)
    # Sharding
    client = util.clients[0]
    current_shard = util.get_shard_index(ctx.guild.id)
    stats_embed.add_field(name=translations.translate(ctx, "util:botstats:Shard"),
                          value=(translations.translate(ctx, "util:botstats:Name", current_shard + 1, client.shard_count, gconf.shard_names[current_shard])
                                 + translations.translate(ctx, "util:botstats:Uptime", util.display_time(time.time() - client.start_time, granularity=4))),
                          inline=False)

    await util.reply(ctx, embed=stats_embed)


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def servers(ctx, **_):
    """util:servers:Help"""

    server_count = util.get_server_count()
    await translations.say(ctx, "util:servers:Response", server_count)


@commands.command(permission=Permission.REAL_SERVER_ADMIN, args_pattern="S", aliases=("sl",))
async def setlanguage(ctx, new_lan, **details):
    """util:setlanguage:Help"""

    if util.filter_string(new_lan) != new_lan:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "util:setlanguage:Error"))

    if str(new_lan) in ("en", "es", "fr"):
        dueserverconfig.set_language(ctx.guild, new_lan)
        await translations.say(ctx, "util:setlanguage:Success", ctx.guild.name, new_lan)
    else:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "util:setlanguage:Error"))


@commands.command(permission=Permission.REAL_SERVER_ADMIN, args_pattern=None)
async def languages(ctx, **_):
    """util:languages:Help"""

    lan_embed = discord.Embed(title="BattleBanana's Localization!", type="rich", color=gconf.DUE_COLOUR)
    lan_embed.description = "en - English\n es - Español\n fr - Français"

    await util.reply(ctx, embed=lan_embed)



@commands.command(permission=Permission.SERVER_ADMIN, args_pattern="S", aliases=("setprefix",))
async def setcmdkey(ctx, new_key, **details):
    """util:setcmdkey:Help"""
    if util.filter_string(new_key) != new_key:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "util:setcmdkey:InvalidKey"))

    if len(new_key) in (1, 2):
        dueserverconfig.server_cmd_key(ctx.guild, new_key)
        await translations.say(ctx, "util:setcmdkey:Success", ctx.guild.name, new_key)
    else:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "util:setcmdkey:InvalidChars"))


@commands.command(permission=Permission.SERVER_ADMIN, args_pattern="S?")
async def shutup(ctx, *args, **details):
    """util:shutup:Help"""

    if len(args) == 0:
        mute_success = dueserverconfig.mute_channel(ctx.channel)
        if mute_success:
            await translations.say(ctx, "util:shutup:MuteSuccess")
        else:
            await translations.say(ctx, "util:shutup:MuteError")
    else:
        mute_level = args[0].lower()
        if mute_level == "all":
            mute_success = dueserverconfig.mute_channel(ctx.channel, mute_all=True)
            if mute_success:
                await translations.say(ctx, "util:shutup:MuteAllSuccess")
            else:
                await translations.say(ctx, "util:shutup:MuteAllError")
        else:
            await translations.say(ctx, "util:shutup:Error")


@commands.command(permission=Permission.REAL_SERVER_ADMIN, args_pattern="S?")
@commands.require_cnf(warning="util:leave:CNF")
async def leave(ctx, **_):
    """util:leave:Help"""

    bye_embed = discord.Embed(title=translations.translate(ctx, "util:leave:Bye"), color=gconf.DUE_COLOUR)
    bye_embed.set_image(url="http://i.imgur.com/N65P9gL.gif")
    await util.reply(ctx, embed=bye_embed)
    try:
        await ctx.guild.leave()
    except:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "util:leave:Error"))


@commands.command(permission=Permission.SERVER_ADMIN, args_pattern=None)
async def unshutup(ctx, **_):
    """util:unshutup:HELP"""
    if dueserverconfig.unmute_channel(ctx.channel):
        await translations.say(ctx, "util:unshutup:Success")
    else:
        await translations.say(ctx, "util:unshutup:NotMuted")


@commands.command(permission=Permission.SERVER_ADMIN, args_pattern="S*")
async def whitelist(ctx, *args, **_):
    """util:whitelist:Help"""

    if len(args) > 0:
        due_commands = events.command_event.command_list(aliases=True)
        whitelisted_commands = set(commands.replace_aliases([command.lower() for command in args]))
        if whitelisted_commands.issubset(due_commands):
            dueserverconfig.set_command_whitelist(ctx.channel, list(whitelisted_commands))
            await translations.say(ctx, "util:whitelist:Success", ', '.join(whitelisted_commands))
        else:
            incorrect_commands = whitelisted_commands.difference(due_commands)
            await translations.say(ctx, "util:whitelist:Error", ', '.join(incorrect_commands))
    else:
        dueserverconfig.set_command_whitelist(ctx.channel, [])
        await translations.say(ctx, "util:whitelist:Reset")


@commands.command(permission=Permission.SERVER_ADMIN, args_pattern="S*")
async def blacklist(ctx, *args, **_):
    """util:blacklist:Help"""

    if len(args) > 0:
        due_commands = events.command_event.command_list(aliases=True)
        blacklisted_commands = set(commands.replace_aliases([command.lower() for command in args]))
        if blacklisted_commands.issubset(due_commands):
            whitelisted_commands = list(set(due_commands).difference(blacklisted_commands))
            whitelisted_commands.append("is_blacklist")
            dueserverconfig.set_command_whitelist(ctx.channel, whitelisted_commands)
            await translations.say(ctx, "util:blacklist:Success", ', '.join(blacklisted_commands))
        else:
            incorrect_commands = blacklisted_commands.difference(due_commands)
            await translations.say(ctx, "util:blacklist:Error", ', '.join(incorrect_commands))
    else:
        dueserverconfig.set_command_whitelist(ctx.channel, [])
        await translations.say(ctx, "util:blacklist:Reset")


@commands.command(permission=Permission.REAL_SERVER_ADMIN, args_pattern=None)
async def setuproles(ctx, **_):
    """util:setuproles:Help"""
    roles_made = await util.set_up_roles(ctx.guild)
    roles_count = len(roles_made)
    if roles_count > 0:
        result = translations.translate(ctx, "util:setuproles:Created", roles_count, util.s_suffix("role", roles_count))
        for role in roles_made:
            result += "→ ``%s``\n" % role["name"]
        await util.reply(ctx, result)
    else:
        await translations.say(ctx, "util:setuproles:NoNew")


async def optout_is_topdog_check(ctx, player):
    topdog = player.is_top_dog()
    if topdog:
        await translations.say(ctx, "other:misc:TopDogCheck")
    return topdog


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def optout(ctx, **details):
    """util:optout:Help"""

    player = details["author"]
    if player.is_playing():
        current_permission = permissions.get_special_permission(ctx.author)
        if await optout_is_topdog_check(ctx, player):
            return
        if current_permission >= Permission.BANANA_MOD:
            raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "util:optout:StaffMember"))
        permissions.give_permission(ctx.author, Permission.DISCORD_USER)
        await util.reply(ctx, translations.translate(ctx, "util:optout:Success"))
    else:
        await util.reply(ctx, translations.translate(ctx, "util:optout:AlreadyOptOut"))


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def optin(ctx, **details):
    """util:optin:Help"""

    player = details["author"]
    local_optout = not player.is_playing(ctx.guild, local=True)
    # Already playing
    if player.is_playing():
        if not local_optout:
            await translations.translate(ctx, "util:optin:AlreadyOptIn")
        else:
            await translations.say(ctx, "util:optin:OptInGuild")
    else:
        permissions.give_permission(ctx.author, Permission.PLAYER)
        await translations.say(ctx, "util:optin:OptInAll")


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def optouthere(ctx, **details):
    """util:optouthere:Help"""

    player = details["author"]

    if not player.is_playing():
        await translations.say(ctx, "util:optouthere:AlreadyOptOut")
        return

    if player.is_playing(ctx.guild, local=True):
        optout_role = util.get_role_by_name(ctx.guild, gconf.OPTOUT_ROLE)
        if optout_role is None:
            await translations.say(ctx, "util:optouthere:NoRole")
        else:
            if await optout_is_topdog_check(ctx, player):
                return
            await ctx.author.add_roles(optout_role)
            await translations.say(ctx, "util:optouthere:Success")
    else:
        await translations.say(ctx, "util:optouthere:Already")


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def optinhere(ctx, **details):
    """util:optinhere:Help"""

    player = details["author"]
    globally_opted_out = not player.is_playing()

    optout_role = util.get_role_by_name(ctx.guild, gconf.OPTOUT_ROLE)
    if optout_role is not None and not player.is_playing(ctx.guild, local=True):
        await ctx.author.remove_roles(optout_role)
        await translations.say(ctx, "util:optinhere:Success")
    else:
        if globally_opted_out:
            await translations.say(ctx, "util:optinhere:Global")
        else:
            await translations.say(ctx, "util:optinhere:NotOptOut")


@commands.command(args_pattern=None)
async def currencies(ctx, **details):
    """util:currencies:Help"""

    link = "https://dash.discoin.zws.im/#/currencies"
    embed = discord.Embed(title=e.DISCOIN + translations.translate(ctx, "util:currencies:Title"), type="rich", color=gconf.DUE_COLOUR)
    for id in discoin.CODES:
        currency = discoin.CODES[id]
        embed.add_field(name=id, value=currency['name'], inline=False)

    if len(embed.fields) == 0:
        embed.add_field(name=translations.translate(ctx, "util:currencies:NError"), value=translations.translate(ctx, "util:currencies:VError"))
    embed.set_footer(text=translations.translate(ctx, "util:currencies:Footer", link))

    await util.reply(ctx, embed=embed)


@commands.ratelimit(cooldown=300, error="util:exchange:RateLimit", save=True)
@commands.command(args_pattern="CS", aliases=["convert"])
async def exchange(ctx, amount, currency, **details):
    """util:exchange:Help"""

    player = details["author"]
    currency = currency.upper()

    if currency == discoin.CURRENCY_CODE:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "util:exchange:SameCurrency", discoin.CURRENCY_CODE, discoin.CURRENCY_CODE))
    if not currency in discoin.CODES:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "util:exchange:BadCurrency"))
    if amount > discoin.MAX_TRANSACTION:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "util:exchange:BreaksLimit", discoin.CURRENCY_CODE, discoin.MAX_TRANSACTION))

    amount = int(amount)
    if player.money - amount < 0:
        await translations.say(ctx, "util:exchange:CantAfford", util.format_number(amount, full_precision=True, money=True), util.format_number(player.money, full_precision=True, money=True))
        return

    try:
        response = await discoin.make_transaction(player.id, amount, currency)
    except Exception as discoin_error:
        util.logger.error("Discoin exchange failed %s", discoin_error)
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "util:exchange:ErrorDiscoin"))

    if response.get('statusCode'):
        code = response.get("statusCode")
        if code >= 500:
            raise util.BattleBananaException(ctx.channel,  (translations.translate(ctx, "util:exchange:ErrorDiscoin")+"%s: %s" % (code, response['error'])))
        elif 400 <= code < 500:
            raise util.BattleBananaException(ctx.channel, (translations.translate(ctx, "util:exchange:ErrorBot")+"%s: %s" % (code, response['error'])))

    await awards.give_award(ctx.channel, player, "Discoin")
    player.money -= amount
    player.save()

    transaction = response
    receipt = discoin.DISCOINDASH + "/" + transaction['id'] + "/show"

    exchange_embed = discord.Embed(title=e.DISCOIN + translations.translate(ctx, "util:exchange:Title"), type="rich", color=gconf.DUE_COLOUR)
    exchange_embed.add_field(name=translations.translate(ctx, "util:exchange:Exchange", discoin.CURRENCY_CODE),
                             value=util.format_number(amount, money=True, full_precision=True))
    exchange_embed.add_field(name=translations.translate(ctx, "util:exchange:RESULT", currency),
                             value="$" + util.format_number_precise(transaction['payout']))
    exchange_embed.add_field(name=translations.translate(ctx, "util:exchange:Receipt"), value=receipt, inline=False)
    exchange_embed.set_footer(text=translations.translate(ctx, "util:exchange:Footer"))

    await util.reply(ctx, embed=exchange_embed)

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

    await util.reply(ctx, "All done!")


@commands.command(args_pattern='S?', aliases=['transdata', 'td'])
@commands.require_cnf(warning="Transferring your data will override your current data, assuming you have any, on TheelUtil!")
@commands.ratelimit(cooldown=604800, error="You can't transfer your data again for **[COOLDOWN]**!", save=True)
async def transferdata(ctx, cnf="", **details):
    reader, writer = await asyncio.open_connection(gconf.other_configs["connectionIP"], gconf.other_configs["connectionPort"])
    attributes_to_remove = ['inventory', 'quests', 'equipped', 'received_wagers', 'awards', 'team', 'donor', 'quest_spawn_build_up']
    message = dict(details["author"])
    for attr in attributes_to_remove:
        try:
            message.pop(attr)
        except KeyError:
            continue
    message = json.dumps(message)
    writer.write(message.encode())
    await util.reply(ctx, "Your data has been sent! It should appear on the other bot within a few seconds!")
    writer.close()
    await writer.wait_closed()

async def get_stuff(self):
    for attr in chain.from_iterable(getattr(cls, '__slots__', []) for cls in self.__class__.__mro__):
        try:
            yield attr
        except AttributeError:
            continue

@commands.command(permission=Permission.BANANA_OWNER, args_pattern=None, aliases=['sss'], hidden=True)
async def startsocketserver(ctx, **details):
    """
    [CMD_KEY]sss

    Only in case the server doesn't boot up in run.py
    """
    global async_server
    loop = asyncio.get_event_loop()
    async_server = await asyncio.start_server(players.handle_client, '', gconf.other_configs["connectionPort"])
    server_port = async_server.sockets[0].getsockname()[1] # get port that the server is on, to confirm it started on 4000
    await util.say(ctx.channel, "Listening on port %s!" % server_port)


@commands.command(permission=Permission.BANANA_OWNER, args_pattern="PS?", aliases=['cldr'], hidden=True)
async def cooldownreset(ctx, player, cooldown=None, **details):
    if cooldown is None:
        player.command_rate_limits = {}
    else:
        if not cooldown in player.command_rate_limits:
            raise util.BattleBananaException("Invalid cooldown")
        player.command_rate_limits.pop(cooldown)
    
    player.save()
    await util.say(ctx.channel, "The target player's cooldowns have been reset!")


@commands.command(permission=Permission.BANANA_OWNER, args_pattern="PS?", aliases=['scld'], hidden=True)
async def showcooldown(ctx, player, **details):
    await util.say(ctx.channel, ["%s" % cooldown for cooldown in player.command_rate_limits])