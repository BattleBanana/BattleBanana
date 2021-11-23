import aiohttp
import asyncio
import discord
import emoji  # The emoji list in this is outdated/not complete.
import io
import logging
import math
import time
from datetime import datetime
from itertools import chain

import generalconfig as gconf
from dueutil import dbconn
from .trello import TrelloClient
from .game import stats

"""
A random jumble of classes & functions that are some how
utilities.

Other than that no two things in this module have much in common
"""

client = None
clients = []
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('battlebanana')
logging.getLogger('discord.state').setLevel(logging.ERROR)

trello_client = TrelloClient(api_key=gconf.trello_api_key,
                             api_token=gconf.trello_api_token)


class DueLog:
    @staticmethod
    async def bot(message, **kwargs):
        await say(gconf.log_channel, ":robot: %s" % message, **kwargs)

    @staticmethod
    async def info(message, **kwargs):
        await say(gconf.log_channel, ":grey_exclamation: %s" % message, **kwargs)

    @staticmethod
    async def concern(message, **kwargs):
        await say(gconf.log_channel, ":warning: %s" % message, **kwargs)

    @staticmethod
    async def error(message, **kwargs):
        await say(gconf.error_channel, ":bangbang: %s" % message, **kwargs)


duelogger = DueLog()


class BotException(Exception):
    pass


class BattleBananaException(BotException):
    def __init__(self, channel, message, **kwargs):
        self.message = message
        self.channel = channel
        self.additional_info = kwargs.get('additional_info', "")

    def get_message(self):
        message = ":bangbang: **" + self.message + "**"
        if self.additional_info != "":
            message += "```css\n" + self.additional_info + "```"
        return message


class DueReloadException(BotException):
    def __init__(self, result_channel):
        self.channel = result_channel


class SendMessagePermMissing(discord.Forbidden):
    def __init__(self, cause):
        self.cause = cause


class SlotPickleMixin:
    """
    Mixin for pickling slots
    MIT - http://code.activestate.com/recipes/578433-mixin-for-pickling-objects-with-__slots__/
    ^ Fuck this utter shite is WRONG and does not account for slot inherits
    """

    def __getstate__(self):
        all_slots = chain.from_iterable(getattr(cls, '__slots__', []) for cls in self.__class__.__mro__)
        return dict(
            (slot, getattr(self, slot))
            for slot in all_slots
            if hasattr(self, slot)
        )

    def __setstate__(self, state):
        for slot, value in state.items():
            setattr(self, slot, value)


async def download_file(url):
    async with aiohttp.ClientSession(conn_timeout=10) as session:
        async with session.get(url) as response:
            file_data = io.BytesIO()
            while True:
                chunk = await response.content.read(128)
                if not chunk:
                    break
                file_data.write(chunk)
            response.release()
            file_data.seek(0)
            return file_data


async def tax(amount, bb):
    #cuddle me mr. tax man
    if amount < 10000:
        return amount

    tax_rate = 0.13 #13%
    taxed_total = math.floor(amount * tax_rate)
    taxed_amount = math.floor(amount - taxed_total)
    
    stats.increment_stat(stats.Stat.MONEY_TAXED, taxed_total)
    if bb is not None:
        bb.money += taxed_total
        bb.save()
    
    return taxed_amount


async def reply(ctx, *args, **kwargs):
    if type(ctx.channel) is str:
        # Guild/Channel id
        server_id, channel_id = ctx.channel.split("/")
        ctx.channel = get_guild(int(server_id)).get_channel(int(channel_id))
    # if type(args[0]) is str:
    #    text = args[0]
    #    if "|" in text:
    #        # args[0] = Translated text
    #        pass
    if asyncio.get_event_loop() != clients[0].loop:
        # Allows it to speak across shards
        clients[0].run_task(reply, *((ctx.channel,) + args), mention_author=False, **kwargs)
    else:
        try:
            return await ctx.reply(*args, mention_author=False, **kwargs)
        except discord.errors.HTTPException:
            return await say(ctx.channel, *args, **kwargs)
        except discord.errors.Forbidden as send_error:
            raise SendMessagePermMissing(send_error)


async def say(channel: discord.TextChannel, *args, **kwargs):
    if type(channel) is str:
        # Guild/Channel id
        server_id, channel_id = channel.split("/")
        channel = get_guild(int(server_id)).get_channel(int(channel_id))
    # if type(args[0]) is str:
    #    text = args[0]
    #    if "|" in text:
    #        # args[0] = Translated text
    #        pass
    if asyncio.get_event_loop() != clients[0].loop:
        # Allows it to speak across shards
        clients[0].run_task(say, *((channel,) + args), **kwargs)
    else:
        try:
            return await channel.send(*args, **kwargs)
        except discord.Forbidden as send_error:
            raise SendMessagePermMissing(send_error)


async def save_old_topdog(player):
    topdogs = dbconn.conn()["Topdogs"]
    topdogs.insert_one({'user_id': player.id, 'date': datetime.utcnow()})


async def typing(channel):
    await channel.trigger_typing()


async def wait_for_message(ctx, author, timeout=120):
    channel = ctx.channel

    def check(message):
        msg = message.content.lower()
        return msg in ("hit", "stand") and message.author == author and message.channel == channel

    try:
        return await clients[0].wait_for('message', timeout=timeout, check=check)
    except asyncio.exceptions.TimeoutError:
        return None


async def edit_message(message, **kwargs):
    content = kwargs.pop("content", " ")
    embed = kwargs.pop("embed", None)

    await message.edit(content=content, embed=embed, **kwargs)


async def fetch_user(user_id):
    user = clients[0].get_user(int(user_id))  # Get user from cache
    if user is None:
        # User not in cache
        user = await clients[0].fetch_user(int(user_id))
    return user


async def delete_message(message):
    await message.delete()


def load_and_update(reference, bot_object):
    for item in dir(reference):
        if item not in dir(bot_object):
            setattr(bot_object, item, getattr(reference, item))
    return bot_object


def get_shard_index(server):
    if isinstance(server, discord.Guild):
        return server.shard_id
    return clients[0].get_guild(server).shard_id


def pretty_time():
    return time.strftime('%H:%M %Z on %b %d, %Y')


def get_server_count():
    return len(clients[0].guilds)


def get_guild_id(source):
    if isinstance(source, int):
        return source
    elif hasattr(source, 'guild'):
        return source.guild.id
    elif isinstance(source, discord.Guild):
        return source.id


def get_guild(server_id: int):
    return clients[0].get_guild(server_id)


def is_today(date: datetime):
    today = datetime.today()
    return (today.day == date.day and today.month == date.month and today.year == date.year)


def is_yesterday(date: datetime):
    today = datetime.today()
    return ((today.day - 1) == date.day and today.month == date.month and today.year == date.year)


def get_channel(channel_id):
    if isinstance(channel_id, int):
        return clients[0].get_channel(channel_id)
    try:
        return clients[0].get_channel(int(channel_id))
    except ValueError:
        return None


def ultra_escape_string(string):
    """
    A simple function to escape all discord crap!
    """

    if not isinstance(string, str):
        return string  # Dick move not to raise a ValueError here.
    escaped_string = string
    escaped = []
    for character in string:
        if not character.isalnum() and not character.isspace() and character not in escaped:
            escaped.append(character)
            escaped_string = escaped_string.replace(character, '\\' + character)

    # Escape the ultra annoying mentions that \@everyone does not block
    # Why? Idk
    escaped_string = escaped_string.replace("@everyone", u"@\u200Beveryone") \
        .replace("@here", u"@\u200Bhere")

    return escaped_string


def format_number(number, **kwargs):
    def small_format():
        nonlocal number
        full_number = '{:,.2f}'.format(number).rstrip('0').rstrip('.')
        return full_number if len(full_number) < 27 else '{:,g}'.format(number)

    def really_large_format():
        nonlocal number
        units = ["Million", "Billion", "Trillion", "Quadrillion", "Quintillion", "Sextillion", "Septillion",
                 "Octillion"]
        reg = len(str(math.floor(number / 1000)))
        if (reg - 1) % 3 != 0:
            reg -= (reg - 1) % 3
        number = number / pow(10, reg + 2)
        try:
            string = " " + units[math.floor(reg / 3) - 1]
        except IndexError:
            string = " Bazillion"
        number = int(number * 100) / float(100)
        formatted_number = '{0:g}'.format(number)
        return formatted_number + string if len(formatted_number) < 17 else str(math.trunc(number)) + string

    if number >= 1000000 and not kwargs.get('full_precision', False):
        formatted = really_large_format()
    else:
        formatted = small_format()
    return formatted if not kwargs.get('money', False) else '¤' + formatted


def format_money(amount):
    return format_number(amount, money=True, full_precision=True)


def format_number_precise(number):
    return format_number(number, full_precision=True)


def char_is_emoji(character):
    emojize = emoji.emojize(character, use_aliases=True)
    demojize = emoji.demojize(emojize)
    return emojize != demojize


def is_server_emoji(guild, possible_emoji):
    if guild is None:
        return False

    possible_emojis = [str(custom_emoji) for custom_emoji in guild.emojis]
    return possible_emoji in possible_emojis


def is_discord_emoji(guild, emoji):
    return char_is_emoji(emoji) or is_server_emoji(guild, emoji)


def clamp(number, min_val, max_val):
    return max(min(max_val, number), min_val)


async def set_up_roles(guild):
    # Due roles that need making.
    roles = [role_name for role_name in gconf.DUE_ROLES if
             not any(role.name == role_name["name"] for role in guild.roles)]
    for role in roles:
        await guild.create_role(name=role["name"], color=discord.Color(role.get("colour", gconf.DUE_COLOUR)))
    return roles


def has_role_name(member, role_name):
    return next((role for role in member.roles if role.name == role_name), False)


def get_role_by_name(guild, role_name):
    return next((role for role in guild.roles if role.name == role_name), None)


def filter_string(string: str) -> str:
    return ''.join([char if char.isprintable() else "?" for char in string])


SUFFIXES = {1: "st", 2: "nd", 3: "rd", 4: "th"}


def int_to_ordinal(number: int) -> str:
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = SUFFIXES.get(number % 10, "th")
    return str(number) + suffix


# Simple time formatter based on "Mr. B" - https://stackoverflow.com/a/24542445
INTERVALS = (
    ('weeks', 604800),  # 60 * 60 * 24 * 7
    ('days', 86400),  # 60 * 60 * 24
    ('hours', 3600),  # 60 * 60
    ('minutes', 60),
    ('seconds', 1),
)


def display_time(seconds, granularity=2):
    result = []

    for name, count in INTERVALS:
        value = seconds // count
        if value:
            seconds -= value * count
            if value == 1:
                name = name.rstrip('s')
            result.append("{:d} {}".format(int(value), name))
    return ', '.join(result[:granularity])


def s_suffix(word, count):
    return word if count == 1 else word + "s"


def load(c):
    global clients
    clients = c
