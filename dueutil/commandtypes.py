import re
import sys

from . import util
from .game import players, teams
from .game.helpers import misc
from .permissions import Permission

# The max number the bot will accept. To avoid issues with crazy big numbers.
MAX_NUMBER = sys.maxsize
MIN_NUMBER = -MAX_NUMBER
STRING_TYPES = ("S", "M")
THOUSANDS_REGEX = re.compile(r"(\,)(\d\d\d)")

NUMBER_MULTIPLIERS = {
    "k": 1000,
    "m": 1000000,
    "b": 1000000000,
    "t": 1000000000000,
}


def strip_thousands_separators(value):
    # Will strip 1000s without crazy 1,,,,,,,,,,000
    # Allowed will also allow incorrect formatting.
    value = re.sub(THOUSANDS_REGEX, r"\2", value)

    multiplier = value[-1].lower()
    if multiplier in NUMBER_MULTIPLIERS:
        value = float(value[:-1]) * NUMBER_MULTIPLIERS[multiplier]

    return value


def parse_team(value):
    team = teams.find_team(value.lower())
    if team is None:
        return False
    return team


def parse_int(value):
    # An int limited between min and max number
    try:
        return util.clamp(int(strip_thousands_separators(value)), MIN_NUMBER, MAX_NUMBER)
    except ValueError:
        return False


def parse_string(value):
    # When is a string not a string?
    """
    This may seem dumb. But not all strings are strings in my
    world. Fuck zerowidth bullshittery & stuff like that.

    -xoxo MacDue
    """
    # Remove zero width bullshit & extra spaces
    value = re.sub(r"[\u200B-\u200D\uFEFF]", "", value.strip())
    # Remove extra spaces/tabs/new lines ect.
    value = " ".join(value.split())
    if len(value) > 0:
        return value
    return False


def parse_count(value):
    # The counting numbers.
    # Natural numbers starting from 1
    int_value = parse_int(value)
    if not int_value:
        return False
    elif int_value - 1 >= 0:
        return int_value


def parse_float(value):
    # Float between min and max number
    try:
        return util.clamp(float(strip_thousands_separators(value)), MIN_NUMBER, MAX_NUMBER)
    except ValueError:
        return False


def parse_player(player_id, called, ctx):
    # A BattleBanana Player
    try:
        player = players.find_player(int(player_id))
        if player is None or not player.is_playing(ctx.author) and called.permission < Permission.BANANA_MOD:
            return False
        return player
    except ValueError:
        return False


base_func_dict = {"T": parse_team, "S": parse_string, "I": parse_int, "C": parse_count, "R": parse_float}


def parse_type(arg_type, value, **extras):
    if arg_type in base_func_dict:
        return base_func_dict[arg_type](value)

    match (arg_type):
        case "P":
            called = extras.get("called")
            ctx = extras.get("ctx")

            return parse_player(value, called, ctx)
        case "M":
            return parse_count(value) or value
        case "B":
            return value.lower() in misc.POSITIVE_BOOLS
        case "%":
            return parse_float(value.rstrip("%"))
