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
from decimal import Decimal
from datetime import datetime
from io import BytesIO
from typing import Literal
from urllib.parse import urlparse

import aiohttp
import discord
import matplotlib.pyplot as plt
import numpy as np
from colour import Color
from discord import Message
from PIL import Image, ImageDraw, ImageFont
from PIL.Image import Resampling

from dueutil import dbconn, util

from .. import awards, customizations, emojis, gamerules, stats, weapons
from ..configs import dueserverconfig
from ..customizations import _Themes
from ..players import Player
from ..quests import ActiveQuest
from . import imagecache
from bson.decimal128 import Decimal128

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

REQUEST_TIMEOUT = 5


def traffic_light(colour_scale):
    # 0 Red to 1 Green
    colour = traffic_lights[int((len(traffic_lights) - 1) * colour_scale)].rgb
    return tuple((int(ci * 255) for ci in colour))


def set_opacity(image: Image.Image, opacity_level: float):
    # Opaque is 1.0, input between 0-1.0
    opacity_level = int(255 * opacity_level)
    pixel_data = list(image.getdata())
    for i, pixel in enumerate(pixel_data):
        pixel_data[i] = pixel[:3] + (opacity_level,)
    image.putdata(pixel_data)
    return image


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
    Returns True if the url returns a response code between 200-300,
    otherwise return False.
    """
    try:
        headers = {"Range": "bytes=0-10", "User-Agent": "BattleBanana", "Accept": "*/*"}

        async with aiohttp.ClientSession() as session:
            async with session.head(url, headers=headers) as response:
                return (response.status in range(200, 300)) and response.content_type.lower().startswith("image")
    except asyncio.TimeoutError:
        util.logger.warning("Timeout error when checking url %s", url)
    except asyncio.CancelledError as e:
        util.logger.warning("Error when checking url %s: %s", url, e)
    finally:
        await session.close()

    return False


async def is_http_https(url: str):
    return url.startswith("http://") or url.startswith("https://")


async def is_url_image(url: str):
    return await is_http_https(url) and await check_url(url) or False


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
    resized_image = imagecache.get_cached_resized_image(url, width, height)

    if resized_image is None:
        resized_image = resize(await load_image_url(url), width, height)
        asyncio.ensure_future(imagecache.cache_resized_image(resized_image, url))

    return resized_image


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
    try:
        avatar = await resize_avatar(player, ctx.channel.guild, 54, 54)
        image.paste(avatar, (10, 10))
    except Exception:
        pass
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
    try:
        avatar = await resize_avatar(quest, ctx.channel.guild, 54, 54)
        image.paste(avatar, (10, 10))
    except Exception:
        pass
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
        quest_avatar = await resize_avatar(quest, None, 28, 28)
        if quest_avatar is not None:
            image.paste(quest_avatar, (20, 46 + 44 * count))
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
    msg = ""
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

    try:
        image.paste(await resize_avatar(player, ctx.channel.guild, 80, 80), (9, 12))
    except Exception:
        pass

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

    try:
        image.paste(await resize_avatar(quest, None, 72, 72), (9, 12))
    except Exception:
        pass

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

    try:
        image.paste(await resize_avatar(player_one, ctx.channel.guild, 54, 54), (9, 9))
    except Exception:
        pass

    try:
        image.paste(
            await resize_avatar(player_two, ctx.channel.guild, 54, 54),
            (width - 9 - 55, 9),
        )
    except Exception:
        pass

    weapon_one = player_one.weapon
    weapon_two = player_two.weapon

    wep_image_one = await resize_image_url(weapon_one.image_url, 30, 30)

    if wep_image_one is None:
        wep_image_one = await resize_image_url(weapons.Weapon.DEFAULT_IMAGE, 30, 30)

    try:
        image.paste(wep_image_one, (6, height - 6 - 30), wep_image_one)
    except Exception:
        image.paste(wep_image_one, (6, height - 6 - 30))

    wep_image_two = await resize_image_url(weapon_two.image_url, 30, 30)

    if wep_image_two is None:
        wep_image_two = await resize_image_url(weapons.Weapon.DEFAULT_IMAGE, 30, 30)
    try:
        image.paste(wep_image_two, (width - 30 - 6, height - 6 - 30), wep_image_two)
    except Exception:
        image.paste(wep_image_two, (width - 30 - 6, height - 6 - 30))

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
    removed_chars = False
    text = re.sub(r"[\u200B-\u200D\uFEFF]", "", text)
    for _ in range(0, len(text)):
        width = draw.textlength(text=text, font=given_font)
        if width > length:
            text = text[: len(text) - 1]
            removed_chars = True
        else:
            if removed_chars:
                if given_font != font_epic:
                    return text[:-1] + "\u2026"
                else:
                    return text[:-3] + "..."
            return text


async def draw_graph(ctx: Message, which):
    stat_docs = {
        "moneygenerated": dbconn.conn()["stats"].find_one({"stat": "moneygenerated"}),
        "moneyremoved": dbconn.conn()["stats"].find_one({"stat": "moneyremoved"}),
    }
    details_moneygenerated = stat_docs["moneygenerated"]["details"]
    details_moneyremoved_full = stat_docs["moneyremoved"]["details"]
    details_moneyremoved = (
        {month: {"sendcash": cmds.get("sendcash", 0)} for month, cmds in details_moneyremoved_full.items()}
        if which == "2"
        else details_moneyremoved_full
    )

    sorted_month_keys = sorted(set(details_moneygenerated.keys()).union(details_moneyremoved.keys()))
    sorted_month_dt = [datetime.strptime(month, "%Y-%m") for month in sorted_month_keys]
    x_positions = np.arange(len(sorted_month_keys))

    all_commands = sorted(
        set(cmd for month_data in details_moneygenerated.values() for cmd in month_data.keys()).union(
            cmd for month_data in details_moneyremoved.values() for cmd in month_data.keys()
        )
    )

    command_color = plt.cm.get_cmap("tab10", len(all_commands))
    command_color_dict = {cmd: command_color(i) for i, cmd in enumerate(all_commands)}
    command_data_net = {cmd: np.zeros(len(sorted_month_keys)) for cmd in all_commands}
    # it gives me a lot of pain to use american english (illiterate english)
    # "That little British vs. American spelling comment is gold. 😂 Keep it forever." - chatgpt

    def as_decimal(val):
        if isinstance(val, Decimal128):
            return val.to_decimal()
        return Decimal(val)

    for i, month in enumerate(sorted_month_keys):
        for cmd in all_commands:
            generated_amount = details_moneygenerated.get(month, {}).get(cmd, 0)
            removed_amount = details_moneyremoved.get(month, {}).get(cmd, 0)
            command_data_net[cmd][i] = as_decimal(generated_amount) - as_decimal(removed_amount)

    plt.figure(figsize=(12, 6))
    bar_width = 0.4
    positive_bottom_values = np.zeros(len(sorted_month_keys))
    negative_bottom_values = np.zeros(len(sorted_month_keys))
    legend_handles, legend_labels = [], []

    def plot_bars(values, bottom_values, color, cmd, shift):
        bar = plt.bar(x_positions + shift, values, width=bar_width, bottom=bottom_values, label=cmd, color=color)
        return bar

    for cmd, values in command_data_net.items():
        positive_values = np.clip(values, 0, None)
        negative_values = np.clip(values, None, 0)

        positive_bar = plot_bars(positive_values, positive_bottom_values, command_color_dict[cmd], cmd, -bar_width / 2)
        positive_bottom_values += positive_values

        plot_bars(negative_values, negative_bottom_values, command_color_dict[cmd], cmd, -bar_width / 2)
        negative_bottom_values += negative_values

        if cmd not in legend_labels:
            legend_handles.append(positive_bar)
            legend_labels.append(cmd)

    total_net_money = np.sum(list(command_data_net.values()), axis=0)
    net_bar = plot_bars(total_net_money, np.zeros(len(sorted_month_keys)), "blue", "Net Money", bar_width / 2)

    for i, net_value in enumerate(total_net_money):
        plt.text(
            x_positions[i] + bar_width / 2,
            net_value + (10 if net_value > 0 else -10),
            f"{int(net_value)}",
            ha="center",
            va="bottom" if net_value > 0 else "top",
            fontsize=9,
            fontweight="bold",
            color="blue",
        )

    max_positive = np.max(positive_bottom_values)
    max_negative = np.min(negative_bottom_values)
    max_abs = max(abs(max_positive), abs(max_negative))
    plt.ylim(-max_abs, max_abs)

    plt.xticks(x_positions, [time.strftime("%Y-%m") for time in sorted_month_dt], rotation=45, fontsize=8)
    plt.xlabel("Time (Monthly)")
    plt.ylabel("Amount")
    plt.title("Net Money Generated and Removed Per Command")
    plt.axhline(0, color="black", linewidth=1)
    plt.grid(True, linestyle="--", alpha=0.5)

    legend_handles.append(net_bar)
    legend_labels.append("Net Money")
    plt.legend(handles=legend_handles, labels=legend_labels, loc="upper left", bbox_to_anchor=(1, 1), fontsize=8)

    plt.tight_layout()
    img_buffer = BytesIO()
    plt.savefig(img_buffer, format="PNG", bbox_inches="tight")
    img_buffer.seek(0)
    plt.close()

    img = Image.open(img_buffer)
    await send_image(ctx, img, "r", file_name="money_graph.png")


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


def _init_banners():
    for banner in customizations.banners.values():
        if banner.image is None:
            banner.image = set_opacity(Image.open("screens/info_banners/" + banner.image_name), 0.9)


_init_banners()
_load_profile_parts()
