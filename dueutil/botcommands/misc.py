from asyncio.futures import Future
import json
import math
import os
import random
import re
import platform
import textwrap
from threading import Thread
import time
import asyncio
import traceback
from contextlib import redirect_stdout
from io import StringIO

import discord
import dueutil.permissions
import generalconfig as gconf
import objgraph

from .. import commands, util, events, dbconn, loader
from ..game import customizations, awards, leaderboards, game, emojis, translations
from ..game.helpers import imagehelper
from ..permissions import Permission


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def permissions(ctx, **_):
    """misc:permissions:Help"""

    permissions_report = ""
    for permission in dueutil.permissions.permissions:
        permissions_report += ("``" + permission.value[1] + "`` → "
                               + (":white_check_mark:" if dueutil.permissions.has_permission(ctx.author,
                                                                                             permission)
                                  else ":no_entry:") + "\n")
    await util.reply(ctx, permissions_report)


@commands.command(args_pattern="S*", hidden=True)
async def test(ctx, *args, **_):
    """A test command"""

    # print(args[0].__dict__)
    # args[0].save()
    # await imagehelper.test(ctx.channel)
    await util.reply(ctx, ("Yo!!! What up dis be my test command fo show.\n"
                                 "I got deedz args ```" + str(args) + "```!"))


@commands.command(args_pattern="RR", hidden=True)
async def add(ctx, first_number, second_number, **_):
    """
    [CMD_KEY]add (number) (number)
    
    One of the first test commands for Due2
    I keep it for sentimental reasons
    
    """

    result = first_number + second_number
    await util.reply(ctx, "Is " + str(result))


@commands.command()
async def wish(*_, **details):
    """misc:wish:Help"""

    player = details["author"]
    player.quest_spawn_build_up += 0.005


@commands.command(permission=Permission.BANANA_MOD, args_pattern="SSSSIP?")
async def uploadbg(ctx, icon, name, description, url, price, submitter=None, **details):
    """
    [CMD_KEY]uploadbg (a bunch of args)
    
    Takes:
      icon
      name
      desc
      url
      price
      
    in that order.
    
    NOTE: Make event/shitty backgrounds (xmas) etc **free** (so we can delete them)
    
    """

    if not (util.char_is_emoji(icon) or util.is_server_emoji(ctx.guild, icon)):
        raise util.BattleBananaException(ctx.channel, "Icon must be emoji available on this guild!")

    if name != util.filter_string(name):
        raise util.BattleBananaException(ctx.channel, "Invalid background name!")
    name = re.sub(' +', ' ', name)

    if name.lower() in customizations.backgrounds:
        raise util.BattleBananaException(ctx.channel, "That background name has already been used!")

    if price < 0:
        raise util.BattleBananaException(ctx.channel, "Cannot have a negative background price!")

    image = await imagehelper.load_image_url(url, raw=True)
    if image is None:
        raise util.BattleBananaException(ctx.channel, "Failed to load image!")

    if not imagehelper.has_dimensions(image, (256, 299)):
        raise util.BattleBananaException(ctx.channel, "Image must be ``256*299``!")

    image_name = name.lower().replace(' ', '_') + ".png"
    image.save('assets/backgrounds/' + image_name)

    try:
        backgrounds_file = open('assets/backgrounds/backgrounds.json', 'r+')
    except IOError:
        backgrounds_file = open('assets/backgrounds/backgrounds.json', 'w+')
    with backgrounds_file:
        try:
            backgrounds = json.load(backgrounds_file)
        except ValueError:
            backgrounds = {}
        backgrounds[name.lower()] = {"name": name, "icon": icon, "description": description, "image": image_name,
                                     "price": price}
        backgrounds_file.seek(0)
        backgrounds_file.truncate()
        json.dump(backgrounds, backgrounds_file, indent=4)

    customizations.backgrounds._load_backgrounds()

    await util.reply(ctx, ":white_check_mark: Background **" + name + "** has been uploaded!")
    await util.duelogger.info("**%s** added the background **%s**" % (details["author"].name_clean, name))

    if submitter is not None:
        await awards.give_award(ctx.channel, submitter, "BgAccepted", "Background Accepted!")


@commands.command(permission=Permission.BANANA_MOD, args_pattern="S")
async def testbg(ctx, url, **_):
    """
    [CMD_KEY]testbg (image url)

    Tests if a background is the correct dimensions.
    
    """

    image = await imagehelper.load_image_url(url)
    if image is None:
        raise util.BattleBananaException(ctx.channel, "Failed to load image!")

    if not imagehelper.has_dimensions(image, (256, 299)):
        width, height = image.size
        await util.reply(ctx, (":thumbsdown: **That does not meet the requirements!**\n"
                                     + "The tested image had the dimensions ``" + str(width)
                                     + "*" + str(height) + "``!\n"
                                     + "It should be ``256*299``!"))
    else:
        await util.reply(ctx, (":thumbsup: **That looks good to me!**\n"
                                     + "P.s. I can't check for low quality images!"))


@commands.command(permission=Permission.BANANA_MOD, args_pattern="S")
async def deletebg(ctx, background_to_delete, **details):
    """
    [CMD_KEY]deletebg (background name)
    
    Deletes a background.
    
    DO NOT DO THIS UNLESS THE BACKGROUND IS FREE
    
    """
    background_to_delete = background_to_delete.lower()
    if background_to_delete not in customizations.backgrounds:
        raise util.BattleBananaException(ctx.channel, "Background not found!")
    if background_to_delete == "default":
        raise util.BattleBananaException(ctx.channel, "Can't delete default background!")
    background = customizations.backgrounds[background_to_delete]

    try:
        with open('assets/backgrounds/backgrounds.json', 'r+') as backgrounds_file:
            backgrounds = json.load(backgrounds_file)
            if background_to_delete not in backgrounds:
                raise util.BattleBananaException(ctx.channel, "You cannot delete this background!")
            del backgrounds[background_to_delete]
            backgrounds_file.seek(0)
            backgrounds_file.truncate()
            json.dump(backgrounds, backgrounds_file, indent=4)
    except IOError:
        raise util.BattleBananaException(ctx.channel,
                                         "Only uploaded backgrounds can be deleted and there are no uploaded backgrounds!")
    os.remove("assets/backgrounds/" + background["image"])

    customizations.backgrounds._load_backgrounds()

    await util.reply(ctx, ":wastebasket: Background **" + background.name_clean + "** has been deleted!")
    await util.duelogger.info(
        "**%s** deleted the background **%s**" % (details["author"].name_clean, background.name_clean))


def cleanup_code(content):
    """Automatically removes code blocks from the code."""
    # remove ```py\n```
    if content.startswith('```') and content.endswith('```'):
        return '\n'.join(content.split('\n')[1:-1])
    else:
        return content


def get_syntax_error(e):
    if e.text is None:
        return f'```py\n{e.__class__.__name__}: {e}\n```'
    return f'```py\n{e.text}{"^":>{e.offset}}\n{e.__class__.__name__}: {e}```'


@commands.command(permission=Permission.BANANA_OWNER, args_pattern="S", aliases=['evaluate'])
async def eval(ctx, body, **details):
    """
    [CMD_KEY]eval (code)

    For 1337 haxors only! Go away!

    Evaluates a code
    """

    env = {
        'bot': util.clients[0],
        'ctx': ctx,
        'channel': ctx.channel,
        'author': ctx.author,
        'guild': ctx.guild,
        'player': details["author"]
    }

    env.update(globals())
    body = cleanup_code(body)
    stdout = StringIO()

    code_in_l = body.split("\n")
    code_in = ""
    for item in code_in_l:
        if item.startswith(" "):
            code_in += f"... {item}\n"
        else:
            code_in += f">>> {item}\n"

    to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

    t1 = time.time()
    try:
        exec(to_compile, env)
    except Exception as e:
        return await util.reply(ctx, f'```py\n{code_in}\n{e.__class__.__name__}: {e}\n```')
    func = env['func']
    try:
        with redirect_stdout(stdout):
            ret = await func()
            t2 = time.time()
            timep = f"#{(round((t2 - t1) * 1000000)) / 1000} ms"
    except Exception:
        value = stdout.getvalue()
        t2 = time.time()
        timep = f"#{(round((t2 - t1) * 1000000)) / 1000} ms"
        await util.reply(ctx, f'```py\n{code_in}\n{value}{traceback.format_exc()}\n{timep}\n```')
    else:
        value = stdout.getvalue()

        if ret is None:
            if value:
                await util.reply(ctx, f'```py\n{code_in}\n{value}\n{timep}\n```')
            else:
                await util.reply(ctx, f"```py\n{code_in}\n{timep}\n```")
        else:
            await util.reply(ctx, f'```py\n{code_in}\n{value}{ret}\n{timep}\n```')


@commands.command(permission=Permission.BANANA_ADMIN, args_pattern="CC?B?", hidden=True)
async def generatecode(ctx, value, count=1, show=True, **details):
    """
    [CMD_KEY]generatecode ($$$) (amount)

    Generates the number of codes (amount) with price ($$$)
    """

    newcodes = ""
    with open("dueutil/game/configs/codes.json", "r+") as code_file:
        codes = json.load(code_file)

        for i in range(count):
            code = "BATTLEBANANAPROMO_%i" % (random.uniform(1000000000, 9999999999))
            while codes.get(code):
                code = "BATTLEBANANAPROMO_%i" % (random.uniform(1000000000, 9999999999))
            codes[code] = value
            if show:
                newcodes += "%s\n" % code

        code_file.seek(0)
        code_file.truncate()
        json.dump(codes, code_file, indent=4)

    if show:
        code_Embed = discord.Embed(title="New codes!", type="rich", colour=gconf.DUE_COLOUR)
        code_Embed.add_field(name="Codes:", value=newcodes)
        code_Embed.set_footer(
            text="These codes can only be used once! Use %sredeem (code) to redeem the prize!" % (details["cmd_key"]))
        await util.reply(ctx, embed=code_Embed)


@commands.command(permission=Permission.BANANA_ADMIN, args_pattern="C?")
async def codes(ctx, page=1, **details):
    """
    [CMD_KEY]codes

    Shows remaining codes
    """

    page = page - 1
    codelist = ""
    with open("dueutil/game/configs/codes.json", "r+") as code_file:
        codes = json.load(code_file)
        codes = list(codes)
        if page != 0 and page * 30 >= len(codes):
            raise util.BattleBananaException(ctx.channel, "Page not found")

        for index in range(len(codes) - 1 - (30 * page), -1, -1):
            code_name = codes[index]
            codelist += "%s\n" % (code_name)
            if len(codelist) == 720:
                break

    code_Embed = discord.Embed(title="New codes!", type="rich", colour=gconf.DUE_COLOUR)
    code_Embed.add_field(name="Codes:", value="%s" % (codelist if len(codelist) != 0 else "No code to display!"))
    code_Embed.set_footer(
        text="These codes can only be used once! Use %sredeem (code) to redeem the prize!" % (details["cmd_key"]))
    await util.reply(ctx, embed=code_Embed)


@commands.command(args_pattern="S")
async def redeem(ctx, code, **details):
    """misc:redeem:Help"""

    with open("dueutil/game/configs/codes.json", "r+") as code_file:
        try:
            codes = json.load(code_file)
        except ValueError:
            codes = {}

        if not codes.get(code):
            code_file.close()
            raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "misc:redeem:Invalid"))

        user = details["author"]
        money = codes[code]

        del codes[code]
        user.money += money
        user.save()

        code_file.seek(0)
        code_file.truncate()
        json.dump(codes, code_file, indent=4)
        code_file.close()

        await translations.say(ctx, "misc:redeem:Success", util.format_money(money))


@commands.command(permission=Permission.BANANA_OWNER, args_pattern="PS")
async def sudo(ctx, victim, command, **_):
    """
    [CMD_KEY]sudo victim command
    
    Infect a victims mind to make them run any command you like!
    """
    if not (ctx.author.id in (115269304705875969, 261799488719552513)):
        util.logger.info(ctx.author.id + " used the command: sudo\nUsing command: %s" % command)
        if (victim.id in (115269304705875969, 261799488719552513)):
            raise util.BattleBananaException(ctx.channel, "You cannot sudo DeveloperAnonymous or Firescoutt")

    try:
        ctx.author = await ctx.guild.fetch_member(victim.id)
        if ctx.author is None:
            # This may not fix all places where author is used.
            ctx.author = victim.to_member(ctx.guild)
            ctx.author.guild = ctx.guild  # Lie about what guild they're on.
        ctx.content = command
        await util.reply(ctx, ":smiling_imp: Sudoing **" + victim.name_clean + "**!")
        await events.command_event(ctx)
    except util.BattleBananaException as command_failed:
        raise util.BattleBananaException(ctx.channel, 'Sudo failed! "%s"' % command_failed.message)


@commands.command(permission=Permission.BANANA_ADMIN, args_pattern="PC")
async def setpermlevel(ctx, player, level, **_):
    if not (ctx.author.id in (115269304705875969, 261799488719552513)):
        util.logger.info(str(ctx.author.id) + " used the command: setpermlevel\n")
        if (player.id in (115269304705875969, 261799488719552513)):
            raise util.BattleBananaException(ctx.channel,
                                             "You cannot change the permissions for DeveloperAnonymous or Firescoutt")

    member = player.to_member(ctx.guild)
    permission_index = level - 1
    permission_list = dueutil.permissions.permissions
    if permission_index < len(permission_list):
        permission = permission_list[permission_index]
        dueutil.permissions.give_permission(member, permission)
        await util.reply(ctx,
                       "**" + player.name_clean + "** permission level set to ``" + permission.value[1] + "``.")
        if permission == Permission.BANANA_MOD:
            await awards.give_award(ctx.channel, player, "Mod", "Become an mod!")
            await util.duelogger.info("**%s** is now a BattleBanana mod!" % player.name_clean)
        elif "Mod" in player.awards:
            player.awards.remove("Mod")
        if permission == Permission.BANANA_ADMIN:
            await awards.give_award(ctx.channel, player, "Admin", "Become an admin!")
            await util.duelogger.info("**%s** is now a BattleBanana admin!" % player.name_clean)
        elif "Admin" in player.awards:
            player.awards.remove("Admin")
        if permission == Permission.BANANA_OWNER:
            await util.duelogger.info("**%s** is now a BattleBanana Owner!" % player.name_clean)
    else:
        raise util.BattleBananaException(ctx.channel, "Permission not found")


@commands.command(permission=Permission.BANANA_ADMIN, args_pattern="P", aliases=["giveban"])
async def ban(ctx, player, **_):
    if (player.id in (115269304705875969, 261799488719552513)):
        raise util.BattleBananaException(ctx.channel, "You cannot ban DeveloperAnonymous or Firescoutt")
    dueutil.permissions.give_permission(player.to_member(ctx.guild), Permission.BANNED)
    await util.reply(ctx, emojis.MACBAN + " **" + player.name_clean + "** banned!")
    await util.duelogger.concern("**%s** has been banned!" % player.name_clean)


@commands.command(permission=Permission.BANANA_ADMIN, args_pattern="P", aliases=["pardon"])
async def unban(ctx, player, **_):
    member = player.to_member(ctx.guild)
    if not dueutil.permissions.has_special_permission(member, Permission.BANNED):
        await util.reply(ctx, "**%s** is not banned..." % player.name_clean)
        return
    dueutil.permissions.give_permission(member, Permission.PLAYER)
    await util.reply(ctx, ":unicorn: **" + player.name_clean + "** has been unbanned!")
    await util.duelogger.info("**%s** has been unbanned" % player.name_clean)


@commands.command(permission=Permission.BANANA_ADMIN, args_pattern=None, hidden=True)
async def bans(ctx, **_):
    bans_embed = discord.Embed(title="Ban list", type="rich", color=gconf.DUE_COLOUR)
    string = ""
    for k, v in dueutil.permissions.special_permissions.items():
        if v == "banned":
            string += "<@%s> (%s)\n" % (k, k)
    bans_embed.add_field(name="There is what I collected about bad people:", value=string or "Nobody is banned!")

    await util.reply(ctx, embed=bans_embed)


@commands.command(permission=Permission.BANANA_ADMIN, args_pattern="P")
async def toggledonor(ctx, player, **_):
    player.donor = not player.donor
    if player.donor:
        await util.reply(ctx, "**%s** is now a donor!" % player.name_clean)
    else:
        await util.reply(ctx, "**%s** is no longer donor" % player.name_clean)


@commands.command(permission=Permission.BANANA_OWNER, args_pattern=None)
async def reloadbot(ctx, **_):
    await util.reply(ctx, ":ferris_wheel: Reloading BattleBanana modules!")
    await util.duelogger.concern("BattleBanana Reloading!")
    loader.reload_modules(packages=loader.COMMANDS)
    raise util.DueReloadException(ctx.channel)


@commands.command(permission=Permission.BANANA_ADMIN, args_pattern="IP*")
async def givecash(ctx, amount, *players, **_):
    toSend = ""
    for player in players:
        player.money += amount
        amount_str = util.format_number(abs(amount), money=True, full_precision=True)
        if amount >= 0:
            toSend += "Added ``" + amount_str + "`` to **" + player.get_name_possession_clean() + "** account!\n"
        else:
            toSend += "Subtracted ``" + amount_str + "`` from **" + player.get_name_possession_clean() + "** account!\n"
        player.save()

    await util.reply(ctx, toSend)


@commands.command(permission=Permission.BANANA_ADMIN, args_pattern="PI")
async def setcash(ctx, player, amount, **_):
    player.money = amount
    amount_str = util.format_number(amount, money=True, full_precision=True)
    await util.reply(ctx, "Set **%s** balance to ``%s``" % (player.get_name_possession_clean(), amount_str))


@commands.command(permission=Permission.BANANA_ADMIN, args_pattern="PI")
async def setprestige(ctx, player, prestige, **_):
    player.prestige_level = prestige
    player.save()
    await util.reply(ctx, "Set prestige to **%s** for **%s**" % (prestige, player.get_name_possession_clean()))


@commands.command(permission=Permission.BANANA_ADMIN, args_pattern="PS")
async def giveaward(ctx, player, award_id, **_):
    if awards.get_award(award_id) is not None:
        await awards.give_award(ctx.channel, player, award_id)
    else:
        raise util.BattleBananaException(ctx.channel, "Award not found!")


@commands.command(permission=Permission.BANANA_ADMIN, args_pattern="PR")
async def giveexp(ctx, player, exp, **_):
    # (attack + strg + accy) * 100
    if exp < 0.1:
        raise util.BattleBananaException(ctx.channel, "The minimum exp that can be given is 0.1!")
    increase_stat = exp / 300
    player.progress(increase_stat, increase_stat, increase_stat,
                    max_exp=math.inf, max_attr=math.inf)
    await util.reply(ctx, "**%s** has been given **%s** exp!"
                   % (player.name_clean, util.format_number(exp, full_precision=True)))
    await game.check_for_level_up(ctx, player)
    player.save()


@commands.command(permission=Permission.BANANA_MOD, args_pattern=None)
async def updateleaderboard(ctx, **_):
    leaderboards.last_leaderboard_update = 0
    await leaderboards.update_leaderboards(ctx)
    await util.reply(ctx, ":ferris_wheel: Updating leaderboard!")


@commands.command(permission=Permission.BANANA_ADMIN, args_pattern=None)
async def updatebot(ctx, **_):
    """
    [CMD_KEY]updatebot
    
    Updates BattleBanana
    
    """

    try:
        sys = platform.platform()
        if "Linux" in sys:
            update_result = await asyncio.create_subprocess_shell('bash update_script.sh',
                                                                    stdout=asyncio.subprocess.PIPE,
                                                                    stderr=asyncio.subprocess.PIPE)
        elif "Windows" in sys:
            update_result = await asyncio.create_subprocess_shell('"C:\\Program Files\\Git\\bin\\bash" update_script.sh',
                                                                    stdout=asyncio.subprocess.PIPE,
                                                                    stderr=asyncio.subprocess.PIPE)
        else:
            raise asyncio.CancelledError()
    except asyncio.CancelledError as updateexc:
        update_result = updateexc.output
    stdout, stderr = await update_result.communicate()
    if stdout:
        update_result = stdout.decode("utf-8")
    elif stderr:
        update_result = stderr.decode("utf-8")
    else:
        update_result = "Something went wrong!"

    if len(update_result.strip()) == 0:
        update_result = "No output."
    update_embed = discord.Embed(title=":gear: Updating BattleBanana!", type="rich", color=gconf.DUE_COLOUR)
    update_embed.description = "Pulling lastest version from **github**!"
    update_embed.add_field(name='Changes', value='```' + update_result + '```', inline=False)
    await util.reply(ctx, embed=update_embed)
    update_result = update_result.strip()
    if not (update_result.endswith("is up to date.") or update_result.endswith("up-to-date.") or update_result == "Something went wrong!"):
        await util.duelogger.concern("BattleBanana updating!")
        os._exit(1)


@commands.command(permission=Permission.BANANA_ADMIN, args_pattern=None)
async def stopbot(ctx, **_):
    await util.reply(ctx, ":wave: Stopping BattleBanana!")
    await util.duelogger.concern("BattleBanana shutting down!")
    await util.clients[0].change_presence(activity=discord.Activity(name="restarting"), status=discord.Status.idle,
                                          afk=True)
    os._exit(0)


@commands.command(permission=Permission.BANANA_ADMIN, args_pattern=None)
async def restartbot(ctx, **_):
    await util.reply(ctx, ":ferris_wheel: Restarting BattleBanana!")
    await util.duelogger.concern("BattleBanana restarting!!")
    await util.clients[0].change_presence(activity=discord.Activity(name="restarting"), status=discord.Status.idle,
                                          afk=True)
    os._exit(1)


@commands.command(permission=Permission.BANANA_ADMIN, args_pattern=None)
async def meminfo(ctx, **_):
    mem_info = StringIO()
    objgraph.show_most_common_types(file=mem_info)
    await util.reply(ctx, "```%s```" % mem_info.getvalue())
    mem_info = StringIO()
    objgraph.show_growth(file=mem_info)
    await util.reply(ctx, "```%s```" % mem_info.getvalue())


@commands.command(args_pattern=None)
async def ping(ctx, **_):
    """misc:pingpong:PingHelp"""
    message = await util.reply(ctx, ":ping_pong:")
    t1 = time.time()
    dbconn.db.command('ping')
    t2 = time.time()
    dbms = round((t2 - t1) * 1000)
    
    apims = round((message.created_at - ctx.created_at).total_seconds() * 1000)

    embed = discord.Embed(title=":ping_pong: Pong!", type="rich", colour=gconf.DUE_COLOUR)
    embed.add_field(name=translations.translate(ctx, "misc:pingpong:BOT"), value="``%sms``" % (apims))
    try:
        latency = round(util.clients[0].latencies[util.get_shard_index(ctx.guild.id)][1] * 1000)

        embed.add_field(name=translations.translate(ctx, "misc:pingpong:API"), value="``%sms``" % (latency))
    except OverflowError:
        embed.add_field(name=translations.translate(ctx, "misc:pingpong:API"), value="``NaN``" % (latency))

    embed.add_field(name=translations.translate(ctx, "misc:pingpong:DB"), value="``%sms``" % (dbms), inline=False)
    await util.edit_message(message, embed=embed)


@commands.command(args_pattern=None, hidden=True)
async def pong(ctx, **_):
    """misc:pingpong:PongHelp"""
    message = await util.reply(ctx, ":ping_pong:")

    apims = round((message.created_at - ctx.created_at).total_seconds() * 1000)
    latency = round(util.clients[0].latencies[util.get_shard_index(ctx.guild.id)][1] * 1000)

    t1 = time.time()
    dbconn.db.command('ping')
    t2 = time.time()
    dbms = round((t2 - t1) * 1000)

    embed = discord.Embed(title=":ping_pong: Pong!", type="rich", colour=gconf.DUE_COLOUR)
    embed.add_field(name=translations.translate(ctx, "misc:pingpong:API"), value="``%sms``" % (latency))
    embed.add_field(name=translations.translate(ctx, "misc:pingpong:BOT"), value="``%sms``" % (apims))
    embed.add_field(name=translations.translate(ctx, "misc:pingpong:DB"), value="``%sms``" % (dbms), inline=False)

    await util.edit_message(message, embed=embed)


@commands.command(args_pattern=None)
async def vote(ctx, **details):
    """misc:vote:Help"""

    Embed = discord.Embed(title=translations.translate(ctx, "misc:vote:Title"), type="rich", colour=gconf.DUE_COLOUR)
    Embed.add_field(name="Vote:", value="[top.gg](https://top.gg/bot/464601463440801792/vote)\n"
                                        "[discordbotlist.com](https://discordbotlist.com/bots/battlebanana/upvote)\n"
                                        "[bots.ondiscord.xyz](https://bots.ondiscord.xyz/bots/464601463440801792)")
    Embed.set_footer(text=translations.translate(ctx, "misc:vote:Footer"))

    await util.reply(ctx, embed=Embed)

# @commands.command(permission=Permission.BANANA_ADMIN, args_pattern=None, hidden=True)
# async def cleartopdogs(ctx, **details):
#     await util.reply(ctx, ":arrows_counterclockwise: Removing every active topdog!")
#     for id, v in sorted(game.players.players.items()):
#         if 'TopDog' in v.awards:
#             v.awards.remove("TopDog")
#             v.save()

#     await util.reply(ctx, "Scan is done! ")
