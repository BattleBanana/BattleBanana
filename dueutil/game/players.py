"""Player related classes & functions"""

import gc
import json
import math
import random
import time
from collections import defaultdict
from copy import copy
from decimal import localcontext
from itertools import chain

import discord
import jsonpickle
import numpy
from bson.decimal128 import Decimal128, create_decimal128_context

import generalconfig as gconf

from .. import dbconn, permissions, util
from ..game import awards, gamerules, weapons
from ..game.helpers.misc import BattleBananaObject, Ring
from ..permissions import Permission
from ..util import SlotPickleMixin
from . import customizations, emojis
from .customizations import Theme

STAT_GAIN_FORMAT = emojis.ATK + ": +%.2f " + emojis.STRG + ": +%.2f " + emojis.ACCY + ": +%.2f"


class FakeMember:
    def __init__(self, user_id: int, name: str = "<Dummy>", roles=None):
        self.id = user_id
        self.mention = f"<@{user_id}>"
        self.name = name
        self.roles = roles or []


class Player(BattleBananaObject, SlotPickleMixin):
    """
    The BattleBanana player!
    This (and a few other classes) are very higgledy-piggledy due to
    being make very early on in development & have been changed so many
    times while trying not to break older versions & code.

    defaultdict is to hold sets of attributes that can be changed/Added to
    randomly.

    It allows attrs to be added automatically
    """

    # These are all the attrbs needed for a player
    # This is meant to optimize players. One caveat all new attributes
    # Must be a misc_stat, inventory item or equipped item
    __slots__ = [
        "level",
        "attack",
        "strg",
        "hp",
        "exp",
        "money",
        "total_exp",
        "accy",
        "last_progress",
        "last_quest",
        "wagers_won",
        "quests_won",
        "quest_day_start",
        "benfont",
        "quests_completed_today",
        "quests",
        "received_wagers",
        "awards",
        "quest_spawn_build_up",
        "donor",
        "misc_stats",
        "equipped",
        "inventory",
        "last_message_hashes",
        "command_rate_limits",
        "team",
        "team_invites",
        "prestige_level",
        "weapon_hidden",
        "gamble_play",
        "last_played",
    ]

    # I expect new types of quests/weapons to be subclasses.

    DEFAULT_FACTORIES = {"equipped": lambda: "default", "inventory": lambda: ["default"]}

    def __init__(self, *args, **kwargs):
        if kwargs.get("loading", False) and len(args) > 0 and isinstance(args[0], (discord.Member, FakeMember)):
            super().__init__(args[0].id, args[0].name)
            return

        if len(args) > 0 and isinstance(args[0], (discord.Member, FakeMember)):
            super().__init__(args[0].id, args[0].name, **kwargs)
        else:
            super().__init__("NO_ID", "BattleBanana Player", **kwargs)

        self.reset()

    def prestige(self):
        ##### STATS #####
        self.prestige_level += 1
        self.level = 1
        self.exp = 0
        self.total_exp = 0
        self.attack = 1
        self.strg = 1
        self.accy = 1
        self.hp = 10

        ##### USAGE STATS #####
        self.last_progress = 0
        self.last_quest = 0
        self.quest_day_start = 0
        self.quests_completed_today = 0
        self.last_message_hashes = Ring(10)

        self.command_rate_limits = {}

        ##### THINGS #####
        self.quests = []
        self.received_wagers = []

        ##### Equiped items
        self.equipped = defaultdict(
            Player.DEFAULT_FACTORIES["equipped"],
            weapon=weapons.NO_WEAPON_ID,
            banner=customizations.Banner.DEFAULT_BANNER,
            theme=customizations.Theme.DEFAULT_THEME,
            background=customizations.Background.DEFAULT_BACKGROUND,
        )

        ##### Inventory. defaultdict so I can add more stuff - without fuss
        ##### Also makes shop simpler
        self.inventory = defaultdict(
            Player.DEFAULT_FACTORIES["inventory"],
            weapons=[],
            themes=self.inventory.get("themes"),
            backgrounds=self.inventory.get("backgrounds"),
            banners=self.inventory.get("banners"),
        )

        self.save()

    def reset(self, discord_user=None):
        ### New rule: The default of all new items MUST have the id default now.

        if discord_user is not None:
            self.name = discord_user.name
        self.benfont = False

        ##### STATS #####
        self.level = 1
        self.exp = 0
        self.total_exp = 0
        self.attack = 1
        self.strg = 1
        self.accy = 1
        self.hp = 10
        self.money = 100
        self.prestige_level = 0

        ##### USAGE STATS #####
        self.last_progress = 0
        self.last_quest = 0
        self.wagers_won = 0
        self.quests_won = 0
        self.quest_day_start = 0
        self.quests_completed_today = 0
        self.last_message_hashes = Ring(10)
        self.weapon_hidden = False
        self.gamble_play = False
        self.last_played = 0

        self.command_rate_limits = {}

        ##### THINGS #####
        self.quests = []
        self.received_wagers = []

        if not hasattr(self, "awards"):
            self.awards = []
        else:
            # Keep special awards even after reset
            kept_awards = [award_id for award_id in self.awards if awards.get_award(award_id).special]
            # To ensure stats don't get weird
            for award_id in set(self.awards) - set(kept_awards):
                awards.update_award_stat(award_id, "times_given", -1)
            self.awards = kept_awards

        # To help the noobz
        self.quest_spawn_build_up = 1

        # lol no
        self.donor = False
        self.team = self.team if hasattr(self, "team") and self.team is not None else None
        self.team_invites = []

        ##### Dumb misc stats (easy to add & remove)
        self.misc_stats = defaultdict(
            int,
            emojis_given=0,
            emojis=0,
            potatoes=0,
            potatoes_given=0,
            average_spelling_correctness=1,
            average_quest_battle_turns=1,
        )

        ##### Equiped items
        self.equipped = defaultdict(
            Player.DEFAULT_FACTORIES["equipped"],
            weapon=weapons.NO_WEAPON_ID,
            banner=customizations.Banner.DEFAULT_BANNER,
            theme=customizations.Theme.DEFAULT_THEME,
            background=customizations.Background.DEFAULT_BACKGROUND,
        )

        ##### Inventory. defaultdict so I can add more stuff - without fuss
        ##### Also makes shop simpler
        self.inventory = defaultdict(
            Player.DEFAULT_FACTORIES["inventory"],
            weapons=[],
            theme=[customizations.Theme.DEFAULT_THEME],
            backgrounds=[customizations.Background.DEFAULT_BACKGROUND],
            banners=[customizations.Banner.DEFAULT_BANNER],
        )

        self.save()

    def prestige_multiplicator(self):
        return self.prestige_level + 1

    def calculate_progress(self, quest, turns, average_turns):
        quest_scale = quest.get_quest_scale()
        avg_player_stat = self.get_avg_stat()

        def attr_gain(stat):
            return max(
                0.01, (stat / avg_player_stat) * quest.level * (turns / average_turns) / 2 * (quest_scale + 0.5) * 3
            )

        # Put some random in the prestige gain so its not a raw 20 * prestige
        max_stats_gain = 100 * self.prestige_multiplicator()
        if self.donor:
            max_stats_gain *= 1.5

        add_strg = min(attr_gain(quest.strg), max_stats_gain)
        # Limit these with add_strg. Since if the quest is super strong. It would not be beatable.
        # Add a little random so the limit is not super visible
        add_attack = min(attr_gain(quest.attack), add_strg * 3 * random.uniform(0.6, 1.5), max_stats_gain)
        add_accy = min(attr_gain(quest.accy), add_strg * 3 * random.uniform(0.6, 1.5), max_stats_gain)

        return add_strg, add_attack, add_accy, max_stats_gain

    def progress(self, attack, strg, accy, **options):
        max_attr = options.get("max_attr", 0.1)
        max_exp = options.get("max_exp", 15)
        self.attack += min(attack, max_attr)
        self.strg += min(strg, max_attr)
        self.accy += min(accy, max_attr)
        exp = min((attack + strg + accy) * 100, max_exp)
        self.exp += exp
        self.total_exp += exp

    def get_owned(self, item_type, all_items):
        return {item_id: item for item_id, item in all_items.items() if item_id in self.inventory[item_type]}

    def get_owned_themes(self):
        return self.get_owned("themes", customizations.themes)

    def get_owned_backgrounds(self):
        return self.get_owned("backgrounds", customizations.backgrounds)

    def get_owned_banners(self):
        return self.get_owned("banners", customizations.banners)

    def get_owned_weapons(self):
        return [
            weapons.get_weapon_from_id(weapon_id)
            for weapon_id in self.inventory["weapons"]
            if weapon_id != weapons.NO_WEAPON_ID
        ]

    def get_weapon(self, weapon_name):
        return next((weapon for weapon in self.get_owned_weapons() if weapon.name.lower() == weapon_name.lower()), None)

    def owns_weapon(self, weapon_name):
        return self.get_weapon(weapon_name) is not None

    def get_name_possession(self):
        if self.name.endswith("s"):
            return self.name + "'"
        return self.name + "'s"

    def get_name_possession_clean(self):
        return util.ultra_escape_string(self.get_name_possession())

    def discard_stored_weapon(self, weapon):
        if weapon.id in self.inventory["weapons"]:
            self.inventory["weapons"].remove(weapon.id)
            return True
        return False

    def store_weapon(self, weapon):
        self.inventory["weapons"].append(weapon.id)

    def weapon_hit(self):
        return random.random() < self.weapon_accy

    async def get_avatar_url(self, guild=None, **extras):
        if guild is None:
            member = extras.get("member")
        else:
            member = await guild.fetch_member(self.id)

        if member is None:
            return ""

        return member.display_avatar.url

    def get_avg_stat(self):
        return sum((self.attack, self.strg, self.accy)) / 4

    def is_top_dog(self):
        return "TopDog" in self.awards

    def is_playing(self, member=None, **extras):
        # Having the perm DISCORD_USER specially set to override PLAYER
        # means you have opted out.
        if self.is_top_dog():
            return True  # Topdog is ALWAYS playing.
        if member is None:
            # Member not passed.
            member = self.to_member()
        if not extras.get("local", False):
            return permissions.has_permission(member, Permission.PLAYER)
        return not util.has_role_name(member, gconf.OPTOUT_ROLE)

    @property
    def item_value_limit(self):
        # Take into account the progress in the current level.
        precise_level = self.level + self.exp / gamerules.get_exp_for_next_level(self.level)
        return int(30 * (math.pow(precise_level, 2) / 3 + 0.5 * math.pow(precise_level + 1, 2) * precise_level))

    @property
    def rank(self):
        return self.level // 10

    @property
    def rank_colour(self):
        rank_colours = self.theme["rankColours"]
        return rank_colours[self.rank % len(rank_colours)]

    @property
    def weapon_accy(self):
        max_value = self.item_value_limit
        price = self.weapon.price if self.weapon.price > 0 else 1
        new_accy = numpy.clip(max_value / price * 100, 1, 86)
        new_accy = self.weapon.accy if new_accy > self.weapon.accy else new_accy
        return new_accy if price > max_value else self.weapon.accy

    @property
    def user_id(self):
        return self.id

    @property
    def weapon(self):
        return weapons.get_weapon_from_id(self.equipped["weapon"])

    @weapon.setter
    def weapon(self, weapon):
        self._setter("weapon", weapon)

    @property
    def background(self):
        current_background = self.equipped["background"]
        if current_background not in customizations.backgrounds:
            if current_background in self.inventory["backgrounds"]:
                self.inventory["backgrounds"].remove(current_background)
            self.equipped["background"] = "default"
        return customizations.backgrounds[self.equipped["background"]]

    @background.setter
    def background(self, background):
        self._setter("background", background)

    @property
    def banner(self):
        banner = customizations.banners.get(
            self.equipped["banner"], customizations.banners[customizations.Banner.DEFAULT_BANNER]
        )
        if not (self.equipped["banner"] in customizations.banners or banner.can_use_banner(self)):
            self.inventory["banners"].remove(self.equipped["banner"])
            self.equipped["banner"] = customizations.Banner.DEFAULT_BANNER
        return banner

    @banner.setter
    def banner(self, banner):
        self._setter("banner", banner)

    @property
    def theme(self):
        current_theme = self.equipped["theme"]
        if current_theme in customizations.themes:
            theme = copy(customizations.themes[current_theme])
        else:
            theme = customizations.themes["default"]
        if theme["background"] != self.equipped["background"]:
            theme["background"] = self.equipped["background"]
        if theme["banner"] != self.equipped["banner"]:
            theme["banner"] = self.equipped["banner"]
        return theme

    @theme.setter
    def theme(self, theme):
        self._setter("theme", theme)
        if not isinstance(theme, Theme):
            theme = customizations.themes[theme]
        self.equipped["banner"] = theme["banner"]
        self.equipped["background"] = theme["background"]

    def to_member(self, guild=None):
        """
        Returns a discord member or a fake member.
        """
        if guild is not None:
            member = guild.get_member(self.id)
            if member is not None:
                return member
        return FakeMember(self.id, self.name)

    def _setter(self, thing, value):
        if isinstance(value, BattleBananaObject):
            self.equipped[thing] = value.id
        elif isinstance(value, str):
            self.equipped[thing] = value
        else:
            raise util.BotException(f"{thing} cannot be set to {value}")

    def __setstate__(self, object_state: dict):
        SlotPickleMixin.__setstate__(self, object_state)
        if not hasattr(self, "command_rate_limits"):
            self.command_rate_limits = {}

        self.last_message_hashes = Ring(10)
        for message in object_state.get("last_message_hashes", []):
            self.last_message_hashes.append(message)

        self.inventory = defaultdict(Player.DEFAULT_FACTORIES["inventory"], **self.inventory)
        self.equipped = defaultdict(Player.DEFAULT_FACTORIES["equipped"], **self.equipped)
        self.misc_stats = defaultdict(int, **self.misc_stats)

        for quest in self.quests:
            quest.quester = self

    def __getstate__(self):
        object_state = dict(SlotPickleMixin.__getstate__(self))

        object_state["quests"] = [jsonpickle.encode(quest) for quest in self.quests]
        object_state["received_wagers"] = [jsonpickle.encode(wager) for wager in self.received_wagers]

        del object_state["id"]

        return object_state

    def to_mongo(self) -> dict:
        """
        Convert the document to a mongo-ready insert/update dict

        Numbers > int64 are converted to bson.decimal128
        """
        document: dict = self.__getstate__()

        for attr, value in document.items():
            if isinstance(value, (int, float)) and abs(value) > 2**63 - 1:
                with localcontext(create_decimal128_context()) as ctx:
                    document[attr] = Decimal128(ctx.create_decimal(value))

        return document

    def __iter__(self):
        for attr in chain.from_iterable(getattr(cls, "__slots__", []) for cls in self.__class__.__mro__):
            try:
                yield attr, getattr(self, attr)
            except AttributeError:
                continue


def find_player(user_id: int) -> Player | None:
    if user_id > 2**63 - 1 or user_id < 0:
        return None

    return load_player(user_id)


REFERENCE_PLAYER = Player(no_save=True)


def load_player(player_id: int) -> Player | None:
    response = dbconn.get_collection_for_object(Player).find_one({"_id": player_id})

    if response is not None:
        player_data = response

        for attr, value in player_data.items():
            if isinstance(value, Decimal128):
                player_data[attr] = float(value.to_decimal())

        player_data["quests"] = [jsonpickle.decode(quest) for quest in player_data["quests"]]
        player_data["received_wagers"] = [jsonpickle.decode(wager) for wager in player_data["received_wagers"]]

        player = Player(FakeMember(player_id, player_data["name"]), loading=True)
        player.__setstate__(player_data)

        return player

    return None


def get_stuff(self):
    for attr in chain.from_iterable(getattr(cls, "__slots__", []) for cls in self.__class__.__mro__):
        try:
            yield from attr
        except AttributeError:
            continue


async def handle_client(reader, writer):
    if writer.get_extra_info("peername")[0] != gconf.other_configs["connectionIP"]:
        util.logger.info(writer.get_extra_info("peername")[0], "tried to connect to us.")
        writer.write("smh".encode())
        writer.close()
        return
    request = (await reader.read()).decode("utf8")
    error_found = False
    try:
        request = json.loads(request)
        player_id = int(request["id"])
        player = find_player(player_id)
        if player is None:  # no account on BattleBanana
            player = Player(FakeMember(player_id))
    except json.decoder.JSONDecodeError as json_error:
        player = None
        error_found = json_error

    if player:
        for attr in set(request.keys()).intersection(get_stuff(player)):  # shared attrs between request and player
            setattr(player, attr, request[attr])
        writer.write("200 OK".encode())
        user: discord.User = util.fetch_user(player.id)
        if user:
            await user.send("Your data has been received and transferred! You can transfer again in 7 days.")
    else:
        writer.write(f"smh {error_found}".encode())
    writer.close()  # close it
