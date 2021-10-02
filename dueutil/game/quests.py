import asyncio
import discord
import json
import jsonpickle
import math
import random
from collections import defaultdict, namedtuple
from typing import Dict, List

from . import gamerules
from .players import Player
from .. import dbconn
from .. import util
from ..game import players
from ..game import weapons
from ..game.helpers.misc import BattleBananaObject, DueMap
from ..util import SlotPickleMixin

quest_map = DueMap()

MIN_QUEST_IV = 0
QUEST_DAY = 86400
QUEST_COOLDOWN = 300
MAX_DAILY_QUESTS = 100
MAX_ACTIVE_QUESTS = 25


class Quest(BattleBananaObject, SlotPickleMixin):
    """A class to hold info about a guild quest"""

    __slots__ = ["server_id", "created_by",
                 "task", "w_id", "spawn_chance", "image_url",
                 "base_attack", "base_strg", "base_accy", "base_hp",
                 "channel", "times_beaten"]

    DEFAULT_IMAGE = "http://i.imgur.com/zOIJM9T.png"

    _BaseStats = namedtuple("BaseStats", ["attack", "strg", "accy", "hp"])

    def __init__(self, name, base_attack, base_strg, base_accy, base_hp, **extras):
        message = extras.get('ctx', None)
        given_spawn_chance = extras.get('spawn_chance', 4)

        if message is not None:
            if message.guild in quest_map:
                if name.lower() in quest_map[message.guild]:
                    raise util.BattleBananaException(message.channel, "A foe with that name already exists on this guild!")

            if base_accy < 1 or base_attack < 1 or base_strg < 1:
                raise util.BattleBananaException(message.channel, "No quest stats can be less than 1!")

            if base_hp < 30:
                raise util.BattleBananaException(message.channel, "Base HP must be at least 30!")

            if len(name) > 30 or len(name) == 0 or name.strip == "":
                raise util.BattleBananaException(message.channel, "Quest names must be between 1 and 30 characters!")

            if given_spawn_chance < 1 or given_spawn_chance > 25:
                raise util.BattleBananaException(message.channel, "Spawn chance must be between 1 and 25%!")

            self.server_id = message.guild.id
            self.created_by = message.author.id
        else:
            self.server_id = extras.get('server_id', "DEFAULT")
            self.created_by = ""

        self.name = name
        super().__init__(self._quest_id(), **extras)
        self.task = extras.get('task', "Battle a")
        self.w_id = extras.get('weapon_id', weapons.NO_WEAPON_ID)
        self.spawn_chance = given_spawn_chance / 100
        self.image_url = extras.get('image_url', Quest.DEFAULT_IMAGE)
        self.base_attack = base_attack
        self.base_strg = base_strg
        self.base_accy = base_accy
        self.base_hp = base_hp
        self.channel = extras.get('channel', "ALL")
        self.times_beaten = 0
        self._add()
        self.save()

    def _quest_id(self):
        return f"{self.server_id}/{self.name.lower()}"

    def _add(self):
        global quest_map
        if self.server_id != "":
            quest_map[self.id] = self

    def base_values(self):
        return self._BaseStats(self.base_attack, self.base_strg,
                               self.base_accy, self.base_hp, )

    def get_channel_mention(self, guild):
        if self.channel in ("ALL", "NONE"):
            return self.channel.title()
        else:
            channel = guild.get_channel(self.channel)
            if channel is None:
                return "``Deleted``"
            else:
                return channel.mention

    @property
    def made_on(self):
        return self.server_id

    @property
    def creator(self):
        creator = players.find_player(self.created_by)
        if creator is not None:
            return creator.name
        else:
            return "Unknown"

    @property
    def q_id(self):
        return self.id

    @property
    def home(self):
        try:
            return util.shard_client.get_guild(self.server_id).name
        except AttributeError:
            return "Unknown"


class ActiveQuest(Player, util.SlotPickleMixin):
    __slots__ = ["level", "attack", "strg", "hp",
                 "equipped", "q_id", "quester_id", "cash_iv",
                 "quester", "accy", "exp", "total_exp"]

    def __init__(self):
        pass  # Use async factory method create instead

    @staticmethod
    async def create(q_id: str, quester: Player):
        # The base quest (holds the quest information)
        active_quest = ActiveQuest()
        active_quest.q_id = q_id
        base_quest = active_quest.info

        active_quest.name = base_quest.name

        active_quest.quester_id = quester.id
        active_quest.quester = quester

        """ The quests equipped items.
           Quests only have weapons but I may add more things a quest
           can have so a default dict will help with that """
        active_quest.equipped = defaultdict(lambda: "default",
                                            weapon=base_quest.w_id)

        target_exp = random.uniform(quester.total_exp, quester.total_exp*1.8)
        active_quest.level = gamerules.get_level_from_exp(target_exp)
        active_quest.total_exp = active_quest.exp = 0
        await active_quest._calculate_stats()
        quester.quests.append(active_quest)
        quester.save()
        return active_quest

    async def _calculate_stats(self):
        base_attack, base_strg, base_accy, base_hp = tuple(base_value / 1.7 for base_value in
                                                           self.info.base_values())
        self.attack = self.accy = self.strg = 1
        target_level = self.level
        self.level = 0
        self.hp = base_hp * target_level * random.uniform(0.6, 1)
        increment_scale = random.uniform(0.4, 1)
        while self.level < target_level:
            exp_next_level = gamerules.get_exp_for_next_level(self.level)
            increment = max(exp_next_level, 1000) * increment_scale / 600
            if self.exp >= exp_next_level:
                self.level += 1
                self.exp = 0
            self.progress(increment * random.uniform(0.6, 1),
                          increment * random.uniform(0.6, 1),
                          increment * random.uniform(0.6, 1),
                          max_attr=math.inf,
                          max_exp=math.inf)
            self.attack += -increment + increment * base_attack
            self.strg += -increment + increment * base_strg
            self.accy += -increment + increment * base_accy
            await asyncio.sleep(1 / 1000)
        self.cash_iv = min(self.info.base_values()) * 3 * random.uniform(0.8, 1.6)

    async def get_avatar_url(self, *args):
        quest_info = self.info
        if quest_info is not None:
            return quest_info.image_url

    def get_reward(self):
        base_reward = self.cash_iv * self.level
        return max(1, int(base_reward + base_reward * (self.get_quest_scale() + 1) * 10))

    def get_quest_scale(self):
        avg_stats = self.get_avg_stat()
        quest_weapon = self.weapon
        quester_weapon = self.quester.weapon
        hp_difference = (self.hp - self.quester.hp) / self.hp / 10
        stat_difference = (avg_stats - self.quester.get_avg_stat()) / avg_stats
        weapon_damage_difference = (quest_weapon.damage - quester_weapon.damage) / quest_weapon.damage
        weapon_accy_difference = (quest_weapon.accy - quester_weapon.accy) / quest_weapon.accy
        return (stat_difference * 10 + weapon_damage_difference
                / 3 + weapon_accy_difference * 5 + hp_difference * 5) / 20

    def get_threat_level(self, player):
        return [
            player.attack / max(player.attack, self.attack),
            player.strg / max(player.strg, self.strg),
            player.accy / max(player.accy, self.accy),
            self.money / max(player.money, self.money),
            player.weapon.damage / max(player.weapon.damage, self.weapon.damage)
        ]

    @property
    def money(self):
        return self.get_reward()

    @money.setter
    def money(self, value):
        pass

    @property
    def info(self):
        return quest_map[self.q_id]

    def save(self):
        pass

    def __setstate__(self, object_state):
        SlotPickleMixin.__setstate__(self, object_state)
        """ quester is set in the player's setstate
        as quests are part of the player's save.
        Also we don't want to inherit the Player setstate.
         """
        self.equipped = defaultdict(self.DEFAULT_FACTORIES["equipped"], **self.equipped)

    def __getstate__(self):
        object_state = SlotPickleMixin.__getstate__(self)
        del object_state["quester"]
        object_state["equipped"] = dict(object_state["equipped"])
        return object_state


def get_server_quest_list(guild: discord.Guild) -> Dict[str, Quest]:
    return quest_map[guild]


def get_quest_on_server(guild: discord.Guild, quest_name: str) -> Quest:
    return quest_map[f"{guild.id}/{quest_name.lower()}"]


def remove_quest_from_server(guild: discord.Guild, quest_name: str):
    quest_id = f"{guild.id}/{quest_name.lower()}"
    del quest_map[quest_id]
    dbconn.get_collection_for_object(Quest).remove({'_id': quest_id})


def get_quest_from_id(quest_id: str) -> Quest:
    return quest_map[quest_id]


def get_channel_quests(channel: discord.abc.GuildChannel) -> List[Quest]:
    return [quest for quest in quest_map[channel.guild].values() if quest.channel in ("ALL", channel.id)]


def get_random_quest_in_channel(channel: discord.abc.GuildChannel):
    if channel.guild in quest_map:
        return random.choice(get_channel_quests(channel))


def add_default_quest_to_server(guild):
    default = random.choice(list(quest_map["DEFAULT"].values()))
    Quest(default.name,
          default.base_attack,
          default.base_strg,
          default.base_accy,
          default.base_hp,
          task=default.task,
          weapon_id=default.w_id,
          image_url=default.image_url,
          spawn_chance=default.spawn_chance * 100,
          server_id=guild.id,
          no_save=False)


def remove_all_quests(guild):
    if guild in quest_map:
        result = dbconn.delete_objects(Quest, '%s/.*' % guild.id)
        del quest_map[guild]
        return result.deleted_count
    return 0


def has_quests(place):
    if isinstance(place, discord.Guild):
        return place in quest_map and len(quest_map[place]) > 0
    elif isinstance(place, discord.abc.GuildChannel):
        if place.guild in quest_map:
            return len(get_channel_quests(place)) > 0
    return False


REFERENCE_QUEST = Quest('Reference', 1, 1, 1, 1, server_id="", no_save=True)


def _load():
    def load_default_quests():
        with open('dueutil/game/configs/defaultquests.json') as defaults_file:
            defaults = json.load(defaults_file)
            for quest_data in defaults.values():
                Quest(quest_data["name"],
                      quest_data["baseAttack"],
                      quest_data["baseStrg"],
                      quest_data["baseAccy"],
                      quest_data["baseHP"],
                      task=quest_data["task"],
                      weapon_id=weapons.stock_weapon(quest_data["weapon"]),
                      image_url=quest_data["image"],
                      spawn_chance=quest_data["spawnChance"],
                      no_save=True)

    load_default_quests()

    for quest in dbconn.get_collection_for_object(Quest).find():
        loaded_quest = jsonpickle.decode(quest['data'])

        if isinstance(loaded_quest.channel, str) and loaded_quest.channel not in ("ALL", None, "NONE"):
            loaded_quest.channel = int(loaded_quest.channel)
        if isinstance(loaded_quest.server_id, str):
            loaded_quest.server_id = int(loaded_quest.server_id)

        quest_map[loaded_quest.id] = util.load_and_update(REFERENCE_QUEST, loaded_quest)
    util.logger.info("Loaded %s quests", len(quest_map))


_load()