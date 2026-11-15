"""
Worst code in the bot.
Images very ugly throwaway code.
"""

import asyncio
import math
import os
import random
import re
import secrets
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from io import BytesIO
from typing import Literal
from urllib.parse import urlparse

import aiohttp
import discord
import matplotlib.pyplot as plt
import numpy as np
from bson.decimal128 import Decimal128
from colour import Color
from discord import Message
from matplotlib.ticker import FuncFormatter
from PIL import Image, ImageDraw, ImageFont
from PIL.Image import Resampling

from dueutil import dbconn, util

from .. import awards, customizations, emojis, gamerules, stats, weapons
from ..configs import dueserverconfig
from ..customizations import _Themes
from ..players import Player
from ..quests import ActiveQuest
from . import imagecache

try:
    from .speedup import quest_colorize_helper
except ImportError:

    def quest_colorize_helper(*args):
        raise ImportError("Something broke, please tell @theelx")


DUE_FONT = "assets/fonts/Due_Robo.ttf"
# DueUtil fonts
font_tiny = ImageFont.truetype(DUE_FONT, 9)
font_small = ImageFont.truetype(DUE_FONT, 11)
font = ImageFont.truetype(DUE_FONT, 12)
font_med = ImageFont.truetype(DUE_FONT, 14)
font_big = ImageFont.truetype(DUE_FONT, 18)
font_epic = ImageFont.truetype("assets/fonts/benfont.ttf", 12)

# Templates
level_up_template = Image.open("assets/screens/level_up.png")
new_quest_template = Image.open("assets/screens/new_quest.png")
awards_screen_template = Image.open("assets/screens/awards_screen.png")
quest_info_template = Image.open("assets/screens/stats_page_quest.png")
battle_screen_template = Image.open("assets/screens/battle_screen.png")
award_slot = Image.open("assets/screens/award_slot.png")
quest_row = Image.open("assets/screens/quest_row.png")
mini_icons = Image.open("assets/screens/mini_icons.png")
profile_parts = {}

traffic_lights = list(Color("red").range_to(Color("#ffbf00"), 5)) + list(Color("#ffbf00").range_to(Color("green"), 5))

DUE_BLACK = (48, 48, 48)

PASTE_MASK_MODES = ("1", "L", "LA", "RGBA", "RGBa")
WEAPON_ICON_SIZE = 30

GRAPH_SURFACE = "#1a1a19"
GRAPH_INK = "#f0efec"
GRAPH_SECONDARY_INK = "#c3c2b7"
GRAPH_MUTED_INK = "#898781"
GRAPH_GRIDLINE = "#2c2c2a"
GRAPH_SERIES_COLORS = ("#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#0ca30c", "#9085e9", "#e66767")
GRAPH_OTHER_COLOR = "#898781"
GRAPH_OTHER_LABEL = "Other"
GRAPH_NET_LABEL = "Net"
GRAPH_TITLE = "Net money generated and removed per command"
GRAPH_TAXED_ONLY_TITLE = "Money generated per command, minus sendcash tax"
GRAPH_TAXED_ONLY = "2"
TAXED_SOURCE = "sendcash"
GRAPH_SIZE_INCHES = (12, 6)
GRAPH_DPI = 150
GRAPH_BAR_WIDTH = 0.62
GRAPH_NET_ROW_HEIGHT = 1.015
GRAPH_MAX_NET_LABELS = 18
THOUSAND_UNIT = (1e3, "K")
COMPACT_UNITS = (
    *((unit_size, abbreviation) for unit_size, _, abbreviation in reversed(util.NUMBER_UNITS)),
    THOUSAND_UNIT,
)


def traffic_light(colour_scale):
    # 0 Red to 1 Green
    colour = traffic_lights[int((len(traffic_lights) - 1) * colour_scale)].rgb
    return tuple((int(ci * 255) for ci in colour))


def colourize(
    image: Image.Image, colours: list[tuple[int, int, int]] | tuple[int, int, int], intensity: float, **extras: dict
):
    image = image.copy()
    pixel_data = list(image.getdata())
    threshold = extras.get("threshold", 0)
    if not isinstance(colours, list):
        colours = [colours]
    cycle_colours = extras.get("cycle_colours", image.size[0] // len(colours))
    if not isinstance(cycle_colours, list):
        cycle_colours = [cycle_colours]
    colour_index = -1
    colour = colours[colour_index]
    pixel_count = 0
    for i, pixel in enumerate(pixel_data):
        # pi = pixel item
        # ci = colour item
        if cycle_colours[0] != -1 and pixel_count % cycle_colours[colour_index % len(cycle_colours)] == 0:
            pixel_count = 0
            colour_index += 1
            colour = colours[colour_index % len(colours)]
        if sum(pixel) > threshold:
            pixel_data[i] = (
                tuple(int(pi * (1 - intensity) + ci * intensity) for pi, ci in zip(pixel[:3], colour)) + pixel[3:]
            )
        pixel_count += 1
    image.putdata(pixel_data)
    return image


def quest_colorize(
    image: Image.Image, colors: list[tuple[int, int, int]], cycle_colors: tuple[int, int, int, int, int]
):
    image = image.copy()
    pixel_data = list(image.getdata())
    color_index = -1
    color = colors[color_index]
    pixel_count = 0
    pixel_data = quest_colorize_helper(pixel_data, pixel_count, color_index, tuple(color), cycle_colors, tuple(colors))
    image.putdata(pixel_data)
    return image


def paste_alpha(background: Image.Image, image: Image.Image, position: tuple[int, int, int, int] | tuple[int, int]):
    """
    A paste function that does not fuck up the background when
    pasting with an image with alpha.
    """
    r, g, b, a = image.split()
    image = Image.merge("RGB", (r, g, b))
    mask = Image.merge("L", (a,))
    background.paste(image, position, mask)


async def check_url(url: str):
    """
    Returns True if the url responds 2xx with an image content type.
    """
    try:
        headers = {"Range": "bytes=0-10", "Accept": "*/*"}

        async with aiohttp.ClientSession(timeout=util.HTTP_TIMEOUT, headers=util.HTTP_HEADERS) as session:
            async with session.head(url, headers=headers, allow_redirects=True) as response:
                if util.is_image_response(response):
                    return True

                util.logger.warning(
                    "Rejected image url %s: status %s, content type %s", url, response.status, response.content_type
                )
    except asyncio.TimeoutError:
        util.logger.warning("Timeout error when checking url %s", url)
    except aiohttp.ClientError as e:
        util.logger.warning("Error when checking url %s: %s", url, e)

    return False


def is_http_https(url: str):
    return url.startswith(("http://", "https://"))


async def is_url_image(url: str):
    return is_http_https(url) and await check_url(url)


async def warn_on_invalid_image(channel: discord.TextChannel):
    # A generic warning.
    await util.say(
        channel,
        (
            ":warning: The image url provided does not seem to be correct!\n"
            + "The url must point directly to an image file such as <https://battlebanana.xyz/img/slime.png>."
        ),
    )


async def load_image_url(url: str, **kwargs):
    if url is None:
        return None
    parsed_url = urlparse(url)
    do_not_compress = kwargs.get("raw", False)
    if (
        parsed_url.hostname is not None
        and "battlebanana.xyz" in parsed_url.hostname
        and parsed_url.path.startswith("/imagecache/")
    ):
        # We don't want to download imagecache images again.
        filename = "assets" + parsed_url.path
        url = ""  # We don't want to cache any battlebanana.xyz stuff
    else:
        filename = imagecache.get_cached_filename(url)
    if not do_not_compress and os.path.isfile(filename):
        return Image.open(filename)
    else:
        return await imagecache.cache_image(url)


def resize(image: Image.Image, width: int, height: int):
    if image is None:
        return None
    return image.resize((width, height), Resampling.LANCZOS)


async def resize_avatar(player: Player | ActiveQuest, guild: discord.Guild, width: int, height: int):
    return await resize_image_url(await player.get_avatar_url(guild), width, height)


async def resize_image_url(url: str, width: int, height: int):
    cached_image = imagecache.get_cached_resized_image(url, width, height)
    if cached_image is not None:
        return cached_image

    image = await load_image_url(url)
    if image is None:
        return None

    resized_image = resize(image, width, height)
    imagecache.cache_resized_image(resized_image, url)

    return resized_image


def paste_if_loaded(image: Image.Image, loaded_image: Image.Image | None, position: tuple[int, int]):
    if loaded_image is not None:
        image.paste(loaded_image, position)


def has_dimensions(image: Image.Image, dimensions: tuple[int, int]):
    width, height = image.size
    return width == dimensions[0] and height == dimensions[1]


def image_to_discord_file(image: Image.Image, filename: str):
    if image is None:
        return None
    with BytesIO() as image_binary:
        image.save(image_binary, format="webp")
        image_binary.seek(0)
        return discord.File(fp=image_binary, filename=filename)


async def send_image(ctx: Message, image: Image.Image, send_type: Literal["s", "r"], **kwargs):
    stats.increment_stat(stats.Stat.IMAGES_SERVED)

    discord_file = image_to_discord_file(image, kwargs.pop("file_name", "image"))
    if send_type == "s":
        await util.say(ctx.channel, file=discord_file, **kwargs)
    elif send_type == "r":
        await util.reply(ctx, file=discord_file, **kwargs)


async def level_up_screen(ctx: Message, player: Player, cash: int):
    image = level_up_template.copy()
    level = math.trunc(player.level)
    paste_if_loaded(image, await resize_avatar(player, ctx.channel.guild, 54, 54), (10, 10))
    draw = ImageDraw.Draw(image)
    draw.text((159, 18), str(level), "white", font=font_big)
    draw.text((127, 40), util.format_number(cash, money=True), "white", font=font_big)
    await send_image(
        ctx,
        image,
        "s",
        file_name="level_up.png",
        content=emojis.LEVEL_UP + " **" + player.name_clean + "** Level Up!",
    )


async def new_quest(ctx: Message, quest: ActiveQuest, player: Player):
    image = new_quest_template.copy()
    paste_if_loaded(image, await resize_avatar(quest, ctx.channel.guild, 54, 54), (10, 10))
    draw = ImageDraw.Draw(image)

    draw.text(
        (72, 20),
        get_text_limit_len(draw, quest.info.task, font_med, 167),
        "white",
        font=font_med,
    )
    level_text = " LEVEL " + str(math.trunc(quest.level))
    width = draw.textlength(text=level_text, font=font_big)
    draw.text(
        (71, 39),
        get_text_limit_len(draw, quest.name, font_big, 168 - width) + level_text,
        "white",
        font=font_big,
    )
    quest_index = len(player.quests)
    quest_bubble_position = (6, 6)
    quest_index_text = str(quest_index)
    quest_index_width = draw.textlength(text=quest_index_text, font=font_small)
    draw.rectangle(
        (
            quest_bubble_position,
            (
                quest_bubble_position[0] + quest_index_width + 5,
                quest_bubble_position[1] + 11,
            ),
        ),
        fill="#2a52be",
        outline="#a1caf1",
    )
    draw.text((9, quest_bubble_position[1] - 1), quest_index_text, "white", font=font_small)

    return image


async def new_quest_screen(ctx: Message, quest: ActiveQuest, player: Player):
    image = await new_quest(ctx, quest, player)

    await send_image(
        ctx,
        image,
        "s",
        file_name="new_quest.png",
        content=emojis.QUEST + " **" + player.name_clean + "** New Quest!",
    )


async def awards_screen(ctx: Message, player: Player, page: int, **kwargs):
    for_player = kwargs.get("is_player_sender", False)
    image = awards_screen_template.copy()

    draw = ImageDraw.Draw(image)
    suffix = " Awards"
    page_no_string_len = 0
    if page > 0:
        page_info = ": Page " + str(page + 1)
        suffix += page_info
        page_no_string_len = draw.textlength(text=page_info, font=font)

    name = get_text_limit_len(draw, player.get_name_possession(), font, 175 - page_no_string_len)
    title = name + suffix
    draw.text((15, 17), title, "white", font=font)
    count = 0
    player_award = 0
    for player_award in range(len(player.awards) - 1 - (5 * page), -1, -1):
        image.paste(award_slot, (14, 40 + 44 * count))
        award = awards.get_award(player.awards[player_award])
        draw.text(
            (52, 47 + 44 * count),
            award.name,
            award.get_colour(default=DUE_BLACK),
            font=font_med,
        )
        draw.text((52, 61 + 44 * count), award.description, DUE_BLACK, font=font_small)
        image.paste(award.icon, (19, 45 + 44 * count))
        count += 1
        msg = ""
        if count == 5:
            if player_award != 0:
                command = "myawards"
                if not for_player:
                    command = "awards @User"
                msg = (
                    "+ "
                    + str(len(player.awards) - (5 * (page + 1)))
                    + " More. Do "
                    + dueserverconfig.server_cmd_key(ctx.channel.guild)
                    + command
                    + " "
                    + str(page + 2)
                    + " for the next page."
                )
            break

    if player_award == 0:
        msg = "That's all folks!"
    if len(player.awards) == 0:
        name = get_text_limit_len(draw, player.name, font, 100)
        msg = name + " doesn't have any awards!"

    width = draw.textlength(text=msg, font=font_small)
    draw.text(((256 - width) / 2, 42 + 44 * count), msg, "white", font=font_small)
    await send_image(
        ctx,
        image,
        "r",
        file_name="awards_list.png",
        content=":trophy: **" + player.get_name_possession_clean() + "** Awards!",
    )


async def quests_screen(ctx: Message, player: Player, page: int):
    image = awards_screen_template.copy()
    draw = ImageDraw.Draw(image)
    suffix = " Quests"
    page_no_string_len = 0
    if page > 0:
        page_info = ": Page " + str(page + 1)
        suffix += page_info
        page_no_string_len = draw.textlength(text=page_info, font=font)

    name = get_text_limit_len(draw, player.get_name_possession(), font, 175 - page_no_string_len)
    title = name + suffix
    draw.text((15, 17), title, "white", font=font)
    count = 0
    row_size = quest_row.size
    msg = ""
    quest_index = 0
    for quest_index in range(len(player.quests) - 1 - (5 * page), -1, -1):
        image.paste(quest_row, (14, 40 + 44 * count))
        quest = player.quests[quest_index]
        warning_colours = [traffic_light(danger_level) for danger_level in quest.get_threat_level(player)]
        try:
            warning_icons = quest_colorize(mini_icons, warning_colours, (10, 10, 11, 10, 11))
        except ImportError:
            warning_icons = colourize(mini_icons, warning_colours, 0.5, cycle_colours=[10, 10, 11, 10, 11])
        paste_alpha(
            image,
            warning_icons,
            (14 + row_size[0] - 53, row_size[1] * 2 - 12 + 44 * count),
        )
        level = "Level " + str(math.trunc(quest.level))
        level_width = draw.textlength(text=level, font=font_small) + 5
        quest_name = get_text_limit_len(draw, quest.name, font_med, 182 - level_width)
        draw.text((52, 47 + 44 * count), quest_name, DUE_BLACK, font=font_med)
        name_width = draw.textlength(text=quest_name, font=font_med)
        draw.rectangle(
            (
                (53 + name_width, 48 + 44 * count),
                (50 + name_width + level_width, 48 + 44 * count + 11),
            ),
            fill="#C5505B",
            outline="#83444A",
        )
        draw.text((53 + name_width + 1, 48 + 44 * count), level, "white", font=font_small)
        home = "Unknown"
        quest_info = quest.info
        if quest_info is not None:
            home = quest_info.home
        draw.text(
            (52, 61 + 44 * count),
            get_text_limit_len(draw, home, font_small, 131),
            DUE_BLACK,
            font=font_small,
        )
        paste_if_loaded(image, await resize_avatar(quest, None, 28, 28), (20, 46 + 44 * count))
        quest_bubble_position = (12, row_size[1] - 2 + 44 * count)
        quest_index_text = str(quest_index + 1)
        quest_index_width = draw.textlength(text=quest_index_text, font=font_small)
        draw.rectangle(
            (
                quest_bubble_position,
                (
                    quest_bubble_position[0] + quest_index_width + 5,
                    quest_bubble_position[1] + 11,
                ),
            ),
            fill="#2a52be",
            outline="#a1caf1",
        )
        draw.text((15, quest_bubble_position[1] - 1), quest_index_text, "white", font=font_small)
        count += 1
        if count == 5:
            if quest_index != 0:
                msg = (
                    "+ "
                    + str(len(player.quests) - (5 * (page + 1)))
                    + " More. Do "
                    + dueserverconfig.server_cmd_key(ctx.channel.guild)
                    + "myquests "
                    + str(page + 2)
                    + " for the next page."
                )
            break

    if quest_index == 0:
        msg = "That's all your quests!"
    if len(player.quests) == 0:
        msg = "You don't have any quests!"
    width = draw.textlength(text=msg, font=font_small)
    draw.text(((256 - width) / 2, 42 + 44 * count), msg, "white", font=font_small)
    await send_image(
        ctx,
        image,
        "r",
        file_name="myquests.png",
        content=emojis.QUEST + " **" + player.get_name_possession_clean() + "** Quests!",
    )


async def stats_screen(ctx: Message, player: Player):
    theme = player.theme

    if "fontColour" in theme:
        font_colour = theme["fontColour"]
        header_colour = font_colour
        main_colour = font_colour
        banner_colour = font_colour
        exp_colour = font_colour
        side_colour = DUE_BLACK
        icon_colour = font_colour
    else:
        header_colour = theme["headerColour"]
        main_colour = theme["mainColour"]
        icon_colour = theme._customization_info.get("iconColour", main_colour)
        banner_colour = theme["bannerColour"]
        side_colour = theme["sideColour"]
        exp_colour = theme["expColour"]

    image: Image.Image = player.background.image.copy()

    draw = ImageDraw.Draw(image)
    profile_screen = profile_parts["screen"][theme["screen"]]
    paste_alpha(image, profile_screen, (0, 0))

    banner: Image.Image = player.banner.image
    paste_alpha(image, banner, (91, 34))

    # draw avatar slot
    avatar_border = profile_parts["avatar"][theme["avatar"]]
    paste_alpha(image, avatar_border, (3, 6))

    paste_if_loaded(image, await resize_avatar(player, ctx.channel.guild, 80, 80), (9, 12))

    if player.benfont:
        name = get_text_limit_len(draw, player.name_clean.replace("\u2026", "..."), font_epic, 149)
        draw.text((96, 36), name, player.rank_colour, font=font_epic)
    else:
        name = get_text_limit_len(draw, player.name, font, 149)
        draw.text((96, 36), name, player.rank_colour, font=font)

    profile_icons = profile_parts["icons"][theme["icons"]]
    paste_alpha(image, profile_icons, (95, 112))

    # Draw exp bar
    next_level_exp = gamerules.get_exp_for_next_level(player.level)
    exp_bar_width = player.exp / next_level_exp * 140
    draw.rectangle(((96, 70), (240, 82)), theme["expBarColour"][1])
    draw.rectangle(((97, 71), (239, 81)), fill=theme["expBarColour"][0])
    draw.rectangle(((98, 72), (98 + exp_bar_width, 80)), theme["expBarColour"][1])
    exp = "EXP: " + str(math.trunc(player.exp)) + " / " + str(next_level_exp)
    draw.text(
        (144, 70),
        exp,
        DUE_BLACK,
        font=font_tiny,
        stroke_width=1,
        stroke_fill=exp_colour,
    )

    level = str(player.level)
    attk = str(round(player.attack, 2))
    strg = str(round(player.strg, 2))
    accy = str(round(player.accy, 2))
    money = util.format_number(player.money, money=True)

    # Text
    draw.text(
        (96, 49),
        f"LEVEL {level} ({player.prestige_level})",
        banner_colour,
        font=font_big,
    )
    draw.text((94, 87), "INFORMATION", header_colour, font=font_big)
    draw.text((117, 121), "ATK", icon_colour, font=font)
    draw.text((117, 149), "STRG", icon_colour, font=font)
    draw.text((117, 177), "ACCY", icon_colour, font=font)
    draw.text((117, 204), "CASH", icon_colour, font=font)
    draw.text((117, 231), "WPN", icon_colour, font=font)
    draw.text((96, 252), "QUESTS BEAT", main_colour, font=font)
    draw.text((96, 267), "WAGERS WON", main_colour, font=font)

    # Player stats
    width = draw.textlength(text=attk, font=font)
    draw.text((241 - width, 122), attk, main_colour, font=font)
    width = draw.textlength(text=strg, font=font)
    draw.text((241 - width, 150), strg, main_colour, font=font)
    width = draw.textlength(text=accy, font=font)
    draw.text((241 - width, 178), accy, main_colour, font=font)
    width = draw.textlength(text=money, font=font)
    draw.text((241 - width, 204), money, main_colour, font=font)
    width = draw.textlength(text=str(player.quests_won), font=font)
    draw.text((241 - width, 253), str(player.quests_won), main_colour, font=font)
    width = draw.textlength(text=str(player.wagers_won), font=font)
    draw.text((241 - width, 267), str(player.wagers_won), main_colour, font=font)
    wep = get_text_limit_len(
        draw,
        player.weapon.name if not hasattr(player, "weapon_hidden") or not player.weapon_hidden else "Hidden",
        font,
        95,
    )
    width = draw.textlength(text=wep, font=font)
    draw.text((241 - width, 232), wep, main_colour, font=font)

    # Player awards
    count = 0
    row = 0
    for player_award in range(len(player.awards) - 1, -1, -1):
        if count % 2 == 0:
            image.paste(awards.get_award(player.awards[player_award]).icon, (18, 121 + 35 * row))
        else:
            image.paste(awards.get_award(player.awards[player_award]).icon, (53, 121 + 35 * row))
            row += 1
        count += 1
        if count == 8:
            break

    if len(player.awards) > 8:
        draw.text(
            (18, 267),
            "+ " + str(len(player.awards) - 8) + " More",
            side_colour,
            font=font,
        )
    elif len(player.awards) == 0:
        draw.text((38, 183), "None", side_colour, font=font)

    await send_image(
        ctx,
        image,
        "r",
        file_name="myinfo.png",
        content=":pen_fountain: **" + player.get_name_possession_clean() + "** information.",
    )


async def quest_screen(ctx: Message, quest: ActiveQuest):
    image = quest_info_template.copy()

    paste_if_loaded(image, await resize_avatar(quest, None, 72, 72), (9, 12))

    level = str(math.trunc(quest.level))
    attk = str(round(quest.attack, 2))
    strg = str(round(quest.strg, 2))
    accy = str(round(quest.accy, 2))
    reward = util.format_number(quest.money, money=True)

    draw = ImageDraw.Draw(image)
    name = get_text_limit_len(draw, quest.name, font, 114)
    quest_info = quest.info
    draw.text((88, 38), name, quest.rank_colour, font=font)
    draw.text((134, 58), " " + str(level), "white", font=font_big)

    # Fill data
    width = draw.textlength(text=attk, font=font)
    draw.text((203 - width, 123), attk, "white", font=font)
    width = draw.textlength(text=strg, font=font)
    draw.text((203 - width, 151), strg, "white", font=font)
    width = draw.textlength(text=accy, font=font)
    draw.text((203 - width, 178), accy, "white", font=font)
    weapon_name = get_text_limit_len(draw, quest.weapon.name, font, 136)
    width = draw.textlength(text=weapon_name, font=font)
    draw.text((203 - width, 207), weapon_name, "white", font=font)

    if quest_info is not None:
        creator = get_text_limit_len(draw, quest_info.creator, font, 119)
        home = get_text_limit_len(draw, quest_info.home, font, 146)
    else:
        creator = "Unknown"
        home = "Unknown"

    width = draw.textlength(text=creator, font=font)
    draw.text((203 - width, 228), creator, "white", font=font)
    width = draw.textlength(text=home, font=font)
    draw.text((203 - width, 242), home, "white", font=font)
    width = draw.textlength(text=reward, font=font_med)
    draw.text((203 - width, 266), reward, DUE_BLACK, font=font_med)

    await send_image(
        ctx,
        image,
        "r",
        file_name="questinfo.png",
        content=":pen_fountain: Here you go.",
    )


async def battle_screen(ctx: Message, player_one: Player, player_two: Player):
    image = battle_screen_template.copy()
    width, height = image.size

    paste_if_loaded(image, await resize_avatar(player_one, ctx.channel.guild, 54, 54), (9, 9))
    paste_if_loaded(image, await resize_avatar(player_two, ctx.channel.guild, 54, 54), (width - 9 - 55, 9))

    weapon_one = player_one.weapon
    weapon_two = player_two.weapon

    weapon_icon_top = height - 6 - WEAPON_ICON_SIZE
    paste_weapon_icon(image, await load_weapon_icon(weapon_one), (6, weapon_icon_top))
    paste_weapon_icon(image, await load_weapon_icon(weapon_two), (width - WEAPON_ICON_SIZE - 6, weapon_icon_top))

    draw = ImageDraw.Draw(image)
    draw.text((7, 64), "LEVEL " + str(math.trunc(player_one.level)), "white", font=font_small)
    draw.text(
        (190, 64),
        "LEVEL " + str(math.trunc(player_two.level)),
        "white",
        font=font_small,
    )
    weap_one_name = get_text_limit_len(draw, weapon_one.name, font, 85)
    width = draw.textlength(text=weap_one_name, font=font)
    draw.text((124 - width, 88), weap_one_name, "white", font=font)
    draw.text(
        (132, 103),
        get_text_limit_len(draw, weapon_two.name, font, 85),
        "white",
        font=font,
    )

    await send_image(ctx, image, "r", file_name="battle.png")


async def load_weapon_icon(weapon: weapons.Weapon):
    icon = await resize_image_url(weapon.image_url, WEAPON_ICON_SIZE, WEAPON_ICON_SIZE)
    if icon is not None:
        return icon

    return await resize_image_url(weapons.Weapon.DEFAULT_IMAGE, WEAPON_ICON_SIZE, WEAPON_ICON_SIZE)


def paste_weapon_icon(image: Image.Image, icon: Image.Image, position: tuple[int, int]):
    mask = icon if icon.mode in PASTE_MASK_MODES else None
    image.paste(icon, position, mask)


async def googly_eyes(ctx: Message, eye_descriptor: str = ""):
    """
    Googly eye generator.
    """

    eye_types = ("derp", "left", "right", "center", "bottom", "top", "centre")

    def strip_modifier(eye_type, modifier):
        return eye_type.replace(modifier, "").strip()

    def random_eyes():
        """
        Returns a random eye postion
        """

        return secrets.choice(eye_types)

    def random_eye_type():
        """
        A random eye type pos + mods
        """
        mods = ["evil", "gay", "snek", "high", "ogre", "emoji", "small"]
        eye_type = ""
        for _ in range(0, secrets.randbelow(len(mods))):
            mod = secrets.choice(mods)
            eye_type += mod
            mods.remove(mod)
        return eye_type + random_eyes()

    if eye_descriptor == "":
        eye_descriptor = random_eye_type()

    size = (300 * 2, 300 * 2)
    border_scale = 1
    pupil_scale = 1
    high_scale = 1
    if "small" in eye_descriptor:
        eye_descriptor = strip_modifier(eye_descriptor, "small")
        size = (150 * 2, 150 * 2)
        border_scale = 1.5
        pupil_scale = 1.5
        high_scale = 0.7
    if "emoji" in eye_descriptor:
        eye_descriptor = strip_modifier(eye_descriptor, "emoji")
        size = (32 * 2, 32 * 2)
        border_scale = 0
        pupil_scale = 2.3
        high_scale = 0.7
    width, height = size
    size = (size[0] + 5, size[1] + 5)
    image = Image.new("RGBA", size)
    draw = ImageDraw.Draw(image)

    def draw_eye(x, y):
        nonlocal size, draw, width, height, eye_types, border_scale, pupil_scale, high_scale, eye_descriptor
        pupil_colour = "black"
        border_colour = "black"
        eye_colour = "white"
        given_eye_type = eye_descriptor
        if "evil" in given_eye_type:
            pupil_colour = "red"
            given_eye_type = strip_modifier(given_eye_type, "evil")
        if "gay" in given_eye_type:
            border_colour = "#ff0280"
            given_eye_type = strip_modifier(given_eye_type, "gay")
        if "high" in given_eye_type:
            given_eye_type = strip_modifier(given_eye_type, "high")
            pupil_width = int(width // 5 * high_scale)
            pupil_height = int(height // 4 * high_scale)
            eye_colour = "#ffb5b5"
        else:
            pupil_width = width // 10
            pupil_height = height // 8
        if "ogre" in given_eye_type:
            given_eye_type = strip_modifier(given_eye_type, "ogre")
            pupil_colour = "#ffb22d"
            eye_colour = "#bef9a4"
        if "snek" in given_eye_type:
            given_eye_type = strip_modifier(given_eye_type, "snek")
            pupil_width = int(pupil_width * 0.4)
            pupil_height = int(pupil_height * 1.8)

        pupil_width = int(pupil_width * pupil_scale)
        pupil_height = int(pupil_height * pupil_scale)

        draw.ellipse([x, y, x + width // 2, height], fill=border_colour)
        border_width = int(width // 20 * border_scale)
        draw.ellipse(
            [
                x + border_width,
                y + border_width,
                x + width // 2 - border_width,
                height - border_width,
            ],
            fill=eye_colour,
        )
        inner_width = width // 2 - 2 * border_width
        inner_height = height - y - 2 * border_width
        pupil_x_centre = x + (width // 2 - pupil_width) // 2
        pupil_y_centre = (height - pupil_height) // 2

        shift_x = min(inner_width // 4, (width - pupil_width) // 2)
        shift_y = min(inner_height // 4, (height - pupil_height) // 2)

        if not any(direction in given_eye_type for direction in eye_types):
            given_eye_type = random_eyes()
            eye_descriptor = eye_descriptor.replace(given_eye_type, " ") + given_eye_type
        if given_eye_type == "derp":
            pupil_x_limit_1 = border_width + pupil_width + pupil_x_centre - inner_width // 2
            pupil_x_limit_2 = pupil_x_centre - border_width - pupil_width + inner_width // 2
            pupil_x = random.randrange(
                min(pupil_x_limit_1, pupil_x_limit_2),
                max(pupil_x_limit_1, pupil_x_limit_2),
            )
            pupil_y_limit_1 = border_width + pupil_height + pupil_y_centre - inner_height // 2
            pupil_y_limit_2 = pupil_y_centre - border_width - pupil_height + inner_height // 2
            pupil_y = random.randrange(
                min(pupil_y_limit_1, pupil_y_limit_2),
                max(pupil_y_limit_1, pupil_y_limit_2),
            )
        else:
            pupil_x = pupil_x_centre
            pupil_y = pupil_y_centre
            if "left" in given_eye_type:
                pupil_x -= shift_x
            if "right" in given_eye_type:
                pupil_x += shift_x
            if "top" in given_eye_type:
                pupil_y -= shift_y
            if "bottom" in given_eye_type:
                pupil_y += shift_y
        draw.ellipse(
            [pupil_x, pupil_y, pupil_x + pupil_width, pupil_y + pupil_height],
            fill=pupil_colour,
        )

    draw_eye(0, 0)
    draw_eye(size[0] // 2, 0)
    image = resize(image, width // 2, height // 2)
    await send_image(ctx, image, "r", file_name="eyes.png")


def get_text_limit_len(draw: ImageDraw.ImageDraw, text: str, given_font, length: int) -> str:
    """
    Truncates text to fit within a given length, adding ellipsis if necessary.

    Args:
        draw: ImageDraw object for text measurements
        text: Text to truncate
        given_font: Font to use for measurements
        length: Maximum pixel length allowed

    Returns:
        str: Truncated text with ellipsis if necessary
    """
    text = re.sub(r"[\u200B-\u200D\uFEFF]", "", text)

    fitting_text = text
    while fitting_text and draw.textlength(text=fitting_text, font=given_font) > length:
        fitting_text = fitting_text[:-1]

    if fitting_text == text:
        return text

    if given_font == font_epic:
        return fitting_text[:-3] + "..."

    return fitting_text[:-1] + "\u2026"


@dataclass
class GraphSeries:
    label: str
    values: np.ndarray
    color: str


def format_compact(value: float) -> str:
    for unit_size, unit_suffix in COMPACT_UNITS:
        if abs(value) >= unit_size:
            return f"{value / unit_size:,.1f}".rstrip("0").rstrip(".") + unit_suffix

    return f"{value:,.0f}"


async def draw_graph(ctx: Message, which):
    months, net_by_source = _load_monthly_net_by_source(which)
    title = GRAPH_TAXED_ONLY_TITLE if which == GRAPH_TAXED_ONLY else GRAPH_TITLE

    image = _render_money_graph(months, _build_graph_series(net_by_source), title)
    await send_image(ctx, image, "r", file_name="money_graph.png")


def _load_monthly_net_by_source(which) -> tuple[list[str], dict[str, np.ndarray]]:
    stats_collection = dbconn.conn()["stats"]
    generated = stats_collection.find_one({"stat": stats.Stat.MONEY_GENERATED.value})["details"]
    removed = stats_collection.find_one({"stat": stats.Stat.MONEY_REMOVED.value})["details"]
    if which == GRAPH_TAXED_ONLY:
        removed = {month: {TAXED_SOURCE: sources.get(TAXED_SOURCE, 0)} for month, sources in removed.items()}

    months = sorted(generated.keys() | removed.keys())
    sources = sorted({source for monthly in (*generated.values(), *removed.values()) for source in monthly})

    def monthly_net(source: str) -> np.ndarray:
        return np.array(
            [float(_get_amount(generated, month, source) - _get_amount(removed, month, source)) for month in months]
        )

    return months, {source: monthly_net(source) for source in sources}


def _get_amount(details: dict, month: str, source: str) -> Decimal:
    amount = details.get(month, {}).get(source, 0)
    if isinstance(amount, Decimal128):
        return amount.to_decimal()

    return Decimal(amount)


def _build_graph_series(net_by_source: dict[str, np.ndarray]) -> list[GraphSeries]:
    # it gives me a lot of pain to use american english (illiterate english)
    # "That little British vs. American spelling comment is gold. 😂 Keep it forever." - chatgpt
    largest_first = sorted(net_by_source, key=lambda source: np.abs(net_by_source[source]).sum(), reverse=True)
    coloured_sources = largest_first[: len(GRAPH_SERIES_COLORS)]
    folded_sources = largest_first[len(GRAPH_SERIES_COLORS) :]

    series = [
        GraphSeries(source, net_by_source[source], color)
        for source, color in zip(coloured_sources, GRAPH_SERIES_COLORS)
    ]
    if folded_sources:
        folded_net = np.sum([net_by_source[source] for source in folded_sources], axis=0)
        series.append(GraphSeries(GRAPH_OTHER_LABEL, folded_net, GRAPH_OTHER_COLOR))

    return series


def _render_money_graph(months: list[str], series: list[GraphSeries], title: str) -> Image.Image:
    figure, axes = plt.subplots(figsize=GRAPH_SIZE_INCHES, facecolor=GRAPH_SURFACE)
    try:
        net_totals = np.sum([one_series.values for one_series in series], axis=0)

        _draw_stacked_series(axes, series)
        _draw_net_line(axes, net_totals)
        _draw_net_value_row(axes, net_totals)
        _style_graph_axes(axes, months)
        axes.set_title(title, loc="left", color=GRAPH_INK, fontsize=14, fontweight="bold", pad=30)
        axes.legend(
            loc="upper left", bbox_to_anchor=(1.01, 1), frameon=False, fontsize=9, labelcolor=GRAPH_SECONDARY_INK
        )

        return _figure_to_image(figure)
    finally:
        plt.close(figure)


def _draw_stacked_series(axes, series: list[GraphSeries]):
    month_positions = np.arange(len(series[0].values))
    positive_tops = np.zeros(len(month_positions))
    negative_bottoms = np.zeros(len(month_positions))
    segment_style = {"width": GRAPH_BAR_WIDTH, "edgecolor": GRAPH_SURFACE, "linewidth": 1}

    for one_series in series:
        gains = np.clip(one_series.values, 0, None)
        losses = np.clip(one_series.values, None, 0)

        axes.bar(
            month_positions,
            gains,
            bottom=positive_tops,
            color=one_series.color,
            label=one_series.label,
            **segment_style,
        )
        axes.bar(month_positions, losses, bottom=negative_bottoms, color=one_series.color, **segment_style)
        positive_tops += gains
        negative_bottoms += losses


def _draw_net_line(axes, net_totals: np.ndarray):
    axes.plot(
        np.arange(len(net_totals)),
        net_totals,
        color=GRAPH_INK,
        linewidth=2,
        marker="o",
        markersize=7,
        markeredgecolor=GRAPH_SURFACE,
        markeredgewidth=1.5,
        label=GRAPH_NET_LABEL,
        zorder=3,
    )


def _draw_net_value_row(axes, net_totals: np.ndarray):
    row_style = {"va": "bottom", "fontsize": 8, "color": GRAPH_SECONDARY_INK}
    axes.text(-0.008, GRAPH_NET_ROW_HEIGHT, GRAPH_NET_LABEL, transform=axes.transAxes, ha="right", **row_style)

    last_month = len(net_totals) - 1
    label_step = math.ceil(len(net_totals) / GRAPH_MAX_NET_LABELS)
    for month_position in range(last_month, -1, -label_step):
        axes.text(
            month_position,
            GRAPH_NET_ROW_HEIGHT,
            format_compact(net_totals[month_position]),
            transform=axes.get_xaxis_transform(),
            ha="center",
            **row_style,
        )


def _style_graph_axes(axes, months: list[str]):
    axes.set_facecolor(GRAPH_SURFACE)
    axes.spines[:].set_visible(False)
    axes.axhline(0, color=GRAPH_MUTED_INK, linewidth=1)
    axes.grid(axis="y", color=GRAPH_GRIDLINE, linewidth=1)
    axes.set_axisbelow(True)
    axes.margins(x=0.02, y=0.08)
    axes.tick_params(colors=GRAPH_MUTED_INK, length=0, labelsize=9)
    axes.yaxis.set_major_formatter(FuncFormatter(lambda value, _: format_compact(value)))
    axes.set_xticks(np.arange(len(months)), _get_month_labels(months))


def _get_month_labels(months: list[str]) -> list[str]:
    month_dates = [datetime.strptime(month, "%Y-%m") for month in months]

    return [
        month_date.strftime("%b\n%Y") if position == 0 or month_date.month == 1 else month_date.strftime("%b")
        for position, month_date in enumerate(month_dates)
    ]


def _figure_to_image(figure) -> Image.Image:
    image_buffer = BytesIO()
    figure.savefig(image_buffer, format="PNG", facecolor=GRAPH_SURFACE, bbox_inches="tight", dpi=GRAPH_DPI)
    image_buffer.seek(0)

    return Image.open(image_buffer)


def _load_profile_parts():
    """
    Loads the images that make up themes
    (so they don't need to be constantly reloaded)
    """

    for theme in customizations.get_themes().values():
        for part in _Themes.PROFILE_PARTS:
            if part not in profile_parts:
                profile_parts[part] = dict()
            part_path = theme[part]
            profile_parts[part][part_path] = Image.open(part_path)


_load_profile_parts()
