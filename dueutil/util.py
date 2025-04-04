"""
A random jumble of classes & functions that are some how
utilities.

Other than that no two things in this module have much in common
"""

import asyncio
import io
import logging
import math
import platform
import time
from datetime import datetime
from itertools import chain

import aiohttp
import cpuinfo
import discord
import emoji  # The emoji list in this is outdated/not complete.
from aiohttp_socks import ProxyConnector

import generalconfig as gconf
from dueutil import dbconn
from dueutil.game import stats

client = None
clients = []
_PROCESSOR = ""
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("battlebanana")
logging.getLogger("discord.state").setLevel(logging.ERROR)


class DueLog:
    """A class for logging things to the log channel"""

    @staticmethod
    async def bot(message, **kwargs):
        await say(gconf.log_channel, f":robot: {message}", **kwargs)

    @staticmethod
    async def info(message, **kwargs):
        await say(gconf.log_channel, f":grey_exclamation: {message}", **kwargs)

    @staticmethod
    async def concern(message, **kwargs):
        await say(gconf.log_channel, f":warning: {message}", **kwargs)

    @staticmethod
    async def error(message, **kwargs):
        await say(gconf.error_channel, f":bangbang: {message}", **kwargs)


duelogger = DueLog()


class BotException(Exception):
    pass


class BattleBananaException(BotException):
    """A class for exceptions that are not errors, but are still worth logging"""

    def __init__(self, channel, message, **kwargs):
        self.message = message
        self.channel = channel
        self.additional_info = kwargs.get("additional_info", "")

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
    MIT - https://code.activestate.com/recipes/578433-mixin-for-pickling-objects-with-__slots__/
    ^ Fuck this utter shite is WRONG and does not account for slot inherits
    """

    def __getstate__(self):
        all_slots = chain.from_iterable(getattr(cls, "__slots__", []) for cls in self.__class__.__mro__)
        return dict((slot, getattr(self, slot)) for slot in all_slots if hasattr(self, slot))

    def __setstate__(self, state):
        for slot, value in state.items():
            setattr(self, slot, value)


def get_vpn_connector():
    vpn_config = gconf.vpn_config
    if vpn_config is None:
        return None

    return ProxyConnector(
        host=vpn_config["host"],
        port=vpn_config["port"],
        username=vpn_config["username"],
        password=vpn_config["password"],
    )


def get_cpu_info():
    global _PROCESSOR
    if _PROCESSOR == "":
        _PROCESSOR = cpuinfo.get_cpu_info()["brand_raw"]
    return _PROCESSOR


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


async def run_script(name: str):
    try:
        sys = platform.platform()
        if "Linux" in sys:
            return await asyncio.create_subprocess_shell(
                f"bash {name}", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
        elif "Windows" in sys:
            return await asyncio.create_subprocess_shell(
                f'"C:\\Program Files\\Git\\bin\\bash" {name}',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        else:
            raise asyncio.CancelledError()
    except asyncio.CancelledError as err:
        return err.output


async def tax(amount, bb, source):
    # in case you ever wanted to do that variable tax rate?
    if amount < 10000: # tax free allowance
        return amount

    tax_rate = 0.13  # 13%
    taxed_total = math.floor(amount * tax_rate)
    taxed_amount = math.floor(amount - taxed_total)

    stats.increment_stat(stats.Stat.MONEY_TAXED, taxed_total)
    stats.increment_stat(stats.Stat.MONEY_REMOVED, taxed_total, source=source)

    if bb is not None:
        bb.money += taxed_total
        bb.save()

    return taxed_amount


async def reply(ctx: discord.Message, *args, **kwargs):
    if isinstance(ctx.channel, str):
        # Guild/Channel id
        server_id, channel_id = ctx.channel.split("/")
        ctx.channel = get_guild(int(server_id)).get_channel(int(channel_id))
    if asyncio.get_event_loop() != clients[0].loop:
        # Allows it to speak across shards
        clients[0].run_task(reply, *((ctx.channel,) + args), mention_author=False, **kwargs)
    else:
        try:
            return await ctx.reply(*args, mention_author=False, **kwargs)
        except discord.errors.HTTPException:
            try:
                return await say(ctx.channel, *args, **kwargs)
            except discord.Forbidden as send_error:
                raise SendMessagePermMissing(send_error) from send_error


async def say(channel: discord.TextChannel, *args, **kwargs):
    if isinstance(channel, str):
        # Guild/Channel id
        server_id, channel_id = channel.split("/")
        channel = get_guild(int(server_id)).get_channel(int(channel_id))
    if asyncio.get_event_loop() != clients[0].loop:
        # Allows it to speak across shards
        clients[0].run_task(say, *((channel,) + args), **kwargs)
    else:
        try:
            return await channel.send(*args, **kwargs)
        except discord.Forbidden as send_error:
            raise SendMessagePermMissing(send_error) from send_error


async def save_old_topdog(player):
    topdogs = dbconn.conn()["Topdogs"]
    topdogs.insert_one({"user_id": player.id, "date": datetime.now()})


async def fetch_user(user_id):
    user = clients[0].get_user(int(user_id))  # Get user from cache
    if user is None:
        # User not in cache
        user = await clients[0].fetch_user(int(user_id))
    return user


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
    return time.strftime("%H:%M %Z on %b %d, %Y")


def get_server_count():
    return len(clients[0].guilds)


def get_shard_count():
    return clients[0].shard_count


def get_guild_id(source):
    if isinstance(source, int):
        return source
    elif hasattr(source, "guild"):
        return source.guild.id
    elif isinstance(source, discord.Guild):
        return source.id


def get_guild(server_id: int) -> discord.Guild:
    return clients[0].get_guild(server_id)


def is_today(date: datetime):
    today = datetime.today()
    return today.day == date.day and today.month == date.month and today.year == date.year


def is_yesterday(date: datetime):
    today = datetime.today()
    return (today.day - 1) == date.day and today.month == date.month and today.year == date.year


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
            escaped_string = escaped_string.replace(character, "\\" + character)

    # Escape the ultra annoying mentions that \@everyone does not block
    # Why? Idk
    escaped_string = escaped_string.replace("@everyone", "@\u200beveryone").replace("@here", "@\u200bhere")

    return escaped_string


def format_number(number, **kwargs):
    def small_format():
        nonlocal number
        full_number = f"{number:,.2f}".rstrip("0").rstrip(".")
        return full_number if len(full_number) < 27 else f"{number:,g}"

    def really_large_format():
        nonlocal number
        units = [
            "Million",
            "Billion",
            "Trillion",
            "Quadrillion",
            "Quintillion",
            "Sextillion",
            "Septillion",
            "Octillion",
        ]
        reg = len(str(math.floor(number / 1000)))
        if (reg - 1) % 3 != 0:
            reg -= (reg - 1) % 3
        number = number / pow(10, reg + 2)
        try:
            string = " " + units[math.floor(reg / 3) - 1]
        except IndexError:
            string = " Bazillion"
        number = int(number * 100) / float(100)
        formatted_number = f"{number:g}"
        return formatted_number + string if len(formatted_number) < 17 else str(math.trunc(number)) + string

    if number >= 1000000 and not kwargs.get("full_precision", False):
        formatted = really_large_format()
    else:
        formatted = small_format()
    return formatted if not kwargs.get("money", False) else "¤" + formatted


def format_money(amount):
    return format_number(amount, money=True, full_precision=True)


def format_number_precise(number):
    return format_number(number, full_precision=True)


def char_is_emoji(character):
    emojize = emoji.emojize(character, language="alias")
    demojize = emoji.demojize(emojize)
    return emojize != demojize


def is_server_emoji(guild, possible_emoji):
    if guild is None:
        return False

    possible_emojis = [str(custom_emoji) for custom_emoji in guild.emojis]
    return possible_emoji in possible_emojis


def is_discord_emoji(guild, possible_emoji):
    return char_is_emoji(possible_emoji) or is_server_emoji(guild, possible_emoji)


def clamp(number, min_val, max_val):
    return max(min(max_val, number), min_val)


async def set_up_roles(guild):
    # Due roles that need making.
    roles = [
        role_name for role_name in gconf.DUE_ROLES if not any(role.name == role_name["name"] for role in guild.roles)
    ]
    for role in roles:
        await guild.create_role(name=role["name"], color=discord.Color(role.get("colour", gconf.DUE_COLOUR)))
    return roles


def has_role_name(member, role_name):
    return next((role for role in member.roles if role.name == role_name), False)


def get_role_by_name(guild, role_name):
    return next((role for role in guild.roles if role.name == role_name), None)


def filter_string(string: str) -> str:
    return "".join([char if char.isprintable() else "?" for char in string])


SUFFIXES = {1: "st", 2: "nd", 3: "rd", 4: "th"}


def int_to_ordinal(number: int) -> str:
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = SUFFIXES.get(number % 10, "th")
    return str(number) + suffix


# Simple time formatter based on "Mr. B" - https://stackoverflow.com/a/24542445
INTERVALS = (
    ("weeks", 604800),  # 60 * 60 * 24 * 7
    ("days", 86400),  # 60 * 60 * 24
    ("hours", 3600),  # 60 * 60
    ("minutes", 60),
    ("seconds", 1),
)

MILLISECOND_INTERVALS = (
    ("weeks", 604800000),  # 1000 * 60 * 60 * 24 * 7
    ("days", 86400000),  # 1000 * 60 * 60 * 24
    ("hours", 3600000),  # 1000 * 60 * 60
    ("minutes", 60000),
    ("seconds", 1000),
    ("ms", 1),
)


def display_time(duration: int | float, granularity=2, milliseconds=False):
    """
    Display a human-readable time duration.

    Args:
        duration (int or float): The time duration in seconds (or milliseconds if milliseconds=True).
        granularity (int): The number of units to include in the output.
        milliseconds (bool): If True, treat 'duration' as milliseconds.

    Returns:
        str: A human-readable string representing the duration.
    """
    if milliseconds:
        intervals = MILLISECOND_INTERVALS
    else:
        intervals = INTERVALS

    result = []
    if milliseconds:
        duration = int(duration)

    for name, count in intervals:
        value = duration // count
        if value > 0:
            duration -= value * count
            if value == 1 and name != "ms":
                name = name.rstrip("s")
            result.append(f"{value} {name}")
    if result:
        return ", ".join(result[:granularity])
    else:
        # If duration is zero or less than the smallest unit
        smallest_unit = intervals[-1][0]
        return f"0 {smallest_unit}"


def s_suffix(word, count):
    return word if count == 1 else word + "s"


def load(c):
    global clients
    clients = c
