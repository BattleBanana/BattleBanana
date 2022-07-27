import discord
import json
import jsonpickle
from collections import namedtuple
from typing import Union, Dict

from . import emojis
from .. import dbconn
from .. import util
from ..game.helpers.misc import BattleBananaObject, DueMap
from ..util import SlotPickleMixin

stock_weapons = ["none"]
weapons = DueMap()

MAX_STORED_WEAPONS = 6

# Simple namedtuple for weapon sums
Summary = namedtuple("Summary", ["price", "damage", "accy"])


class Weapon(BattleBananaObject, SlotPickleMixin):
    """A simple weapon that can be used by a monster or player in BattleBanana"""

    PRICE_CONSTANT = 0.04375
    DEFAULT_IMAGE = "http://i.imgur.com/QFyiU6O.png"

    __slots__ = ["damage", "accy", "price",
                 "_icon", "hit_message", "melee", "image_url",
                 "weapon_sum", "server_id"]

    def __init__(self, name, hit_message, damage, accy, **extras):
        message = extras.get('ctx', None)

        if message is not None:
            if does_weapon_exist(message.guild.id, name):
                raise util.BattleBananaException(message.channel, "A weapon with that name already exists on this guild!")

            if not Weapon.acceptable_string(name, 30):
                raise util.BattleBananaException(message.channel, "Weapon names must be between 1 and 30 characters!")

            if not Weapon.acceptable_string(hit_message, 32):
                raise util.BattleBananaException(message.channel, "Hit message must be between 1 and 32 characters!")

            if accy == 0 or damage == 0:
                raise util.BattleBananaException(message.channel, "No weapon stats can be zero!")

            if accy < 1 or accy > 86:
                raise util.BattleBananaException(message.channel, "Accuracy must be between 1% and 86%!")

            icon = extras.get('icon', emojis.DAGGER)
            if not (util.char_is_emoji(icon) or util.is_server_emoji(message.guild, icon)):
                raise util.BattleBananaException(message.channel, (":eyes: Weapon icons must be emojis! :ok_hand:**"
                                                              + "(custom emojis must be on this guild)**​"))

            self.server_id = message.guild.id

        else:
            self.server_id = "STOCK"

        self.name = name
        self.damage = damage
        self.accy = accy / 100
        self.price = self._price()

        super().__init__(self._weapon_id(), **extras)

        self._icon = extras.get('icon', emojis.DAGGER)
        self.hit_message = util.ultra_escape_string(hit_message)
        self.melee = extras.get('melee', True)
        self.image_url = extras.get('image_url', Weapon.DEFAULT_IMAGE)

        self.weapon_sum = self._weapon_sum()
        self._add()

    @property
    def w_id(self):
        return self.id

    def _weapon_id(self):
        return "%s+%s/%s" % (self.server_id, self._weapon_sum(), self.name.lower())

    def _weapon_sum(self):
        return "%d|%d|%.2f" % (self.price, self.damage, self.accy)

    def _price(self):
        return int(self.accy * self.damage / self.PRICE_CONSTANT) + 1

    def _add(self):
        weapons[self.w_id] = self
        self.save()

    def get_summary(self) -> Summary:
        return get_weapon_summary_from_id(self.id)

    def is_stock(self):
        return self.server_id == "STOCK"

    @property
    def icon(self):
        # Handles custom emojis for weapons being removed.
        # Not the best place for it but it has to go somewhere.
        if self.server_id != "STOCK" and not util.char_is_emoji(self._icon):
            guild = util.get_guild(self.server_id)
            if not util.is_server_emoji(guild, self._icon):
                self.icon = emojis.MISSING_ICON
                self.save()
        return self._icon

    @icon.setter
    def icon(self, icon):
        self._icon = icon

    def __setstate__(self, object_state):
        updated = False
        if "icon" in object_state:
            # Update weapons icon -> _icon
            object_state["_icon"] = object_state["icon"]
            del object_state["icon"]
            updated = True

        SlotPickleMixin.__setstate__(self, object_state)

        if not hasattr(self, "server_id"):
            # Fix an old bug. Weapons missing server_id.
            # Get the proper server_id from the first part of the id.
            self.server_id = self.id.split('+')[0]
            updated = True

        if updated:
            self.save()

# The 'None'/No weapon weapon
NO_WEAPON = Weapon("None", None, 1, 66, no_save=True, image_url="http://i.imgur.com/gNn7DyW.png", icon="👊")
NO_WEAPON_ID = NO_WEAPON.id


def get_weapon_from_id(weapon_id: str) -> Weapon:
    if weapon_id in weapons:
        weapon = weapons[weapon_id]
        # Getting from the store WILL not ensure an exact match.
        # It will only use the name and guild id.
        # We must compare here to ensure the meta data is the same.
        if weapon.id == weapon_id:
            return weapon
    return weapons[NO_WEAPON_ID]


def does_weapon_exist(server_id: int, weapon_name: str) -> bool:
    return get_weapon_for_server(server_id, weapon_name) is not None


def get_weapon_for_server(server_id: int, weapon_name: str) -> Weapon:
    if weapon_name.lower() in stock_weapons:
        return weapons["STOCK/" + weapon_name.lower()]
    weapon_id = f"{server_id}/{weapon_name.lower()}"
    if weapon_id in weapons:
        return weapons[weapon_id]


def get_weapon_summary_from_id(weapon_id: str) -> Summary:
    summary = weapon_id.split('/', 1)[0].split('+')[1].split('|')
    return Summary(price=int(summary[0]),
                   damage=int(summary[1]),
                   accy=float(summary[2]))


def remove_weapon_from_shop(guild: discord.Guild, weapon_name: str) -> bool:
    weapon = get_weapon_for_server(guild.id, weapon_name)
    if weapon is not None:
        del weapons[weapon.id]
        dbconn.get_collection_for_object(Weapon).delete_one({'_id': weapon.id})
        return True
    return False


def get_weapons_for_server(guild: discord.Guild) -> Dict[str, Weapon]:
    return dict(weapons[guild], **weapons["STOCK"])


def find_weapon(guild: discord.Guild, weapon_name_or_id: str) -> Union[Weapon, None]:
    weapon = get_weapon_for_server(guild.id, weapon_name_or_id)
    if weapon is None:
        weapon_id = weapon_name_or_id.lower()
        weapon = get_weapon_from_id(weapon_id)
        if weapon.w_id == NO_WEAPON_ID and weapon_id != NO_WEAPON_ID:
            return None
    return weapon


def stock_weapon(weapon_name: str) -> str:
    if weapon_name in stock_weapons:
        return "STOCK/" + weapon_name
    return NO_WEAPON_ID


def remove_all_weapons(guild):
    if guild in weapons:
        result = dbconn.delete_objects(Weapon, '%s\+.*' % guild.id)
        del weapons[guild]
        return result.deleted_count
    return 0


def _load():
    def load_stock_weapons():
        with open('dueutil/game/configs/defaultweapons.json') as defaults_file:
            defaults = json.load(defaults_file)
            for weapon_name, weapon_data in defaults.items():
                stock_weapons.append(weapon_name)
                Weapon(weapon_data["name"],
                       weapon_data["useText"],
                       weapon_data["damage"],
                       weapon_data["accy"],
                       icon=weapon_data["icon"],
                       image_url=weapon_data["image"],
                       melee=weapon_data["melee"],
                       no_save=True)

    load_stock_weapons()

    # Load from db
    for weapon in dbconn.get_collection_for_object(Weapon).find():
        loaded_weapon: Weapon = jsonpickle.decode(weapon['data'])

        if isinstance(loaded_weapon.server_id, str):
            loaded_weapon.server_id = int(loaded_weapon.server_id)
            
        weapons[loaded_weapon.id] = loaded_weapon
    util.logger.info("Loaded %s weapons", len(weapons))


_load()