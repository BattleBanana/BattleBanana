"""
BattleBanana permissions
"""

from enum import Enum
from functools import total_ordering

import generalconfig as gconf
from dueutil import dbconn, util

special_permissions = {}


@total_ordering
class Permission(Enum):
    """Permissions for BattleBanana"""

    def __lt__(self, other):
        return permissions.index(self) < permissions.index(other)

    BANNED = (lambda member: has_special_permission(member, permissions[0]), "banned", "NoInherit")
    DISCORD_USER = (
        lambda member: (
            has_special_permission(member, permissions[1]) or util.has_role_name(member, gconf.OPTOUT_ROLE)
        ),
        "discord_user",
    )
    PLAYER = (
        lambda _: True,
        "player",
    )
    SERVER_ADMIN = (
        lambda member: (member.guild_permissions.manage_guild or util.has_role_name(member, gconf.COMMANDER_ROLE)),
        "server_admin",
    )
    REAL_SERVER_ADMIN = (lambda member: member.guild_permissions.manage_guild, "real_server_admin")
    BANANA_MOD = (
        lambda member: has_special_permission(member, permissions[5]),
        "BattleBanana_mod",
    )
    BANANA_ADMIN = (
        lambda member: has_special_permission(member, permissions[6]),
        "BattleBanana_admin",
    )
    BANANA_OWNER = (
        lambda member: has_special_permission(member, permissions[7]),
        "BattleBanana_owner",
    )


permissions = list(Permission)


def has_permission(member, permission):
    if permission != Permission.BANNED and not has_special_permission(member, Permission.BANNED):
        if permission == Permission.PLAYER and Permission.DISCORD_USER.value[0](member):
            # If a user has the perm DISCORD_USER specially set to overwrite PLAYER they have opted out.
            return False
        if permission.value[0](member) or has_special_permission(member, permission):
            return True
        elif len(permission.value) < 3:
            for higher_permission in permissions[permissions.index(permission) :]:
                if higher_permission.value[0](member):
                    return True
    return False


def has_special_permission(member, permission):
    return member.id in special_permissions and special_permissions[member.id] == permission.value[1]


def give_permission(member, permission):
    if permission != Permission.PLAYER:
        dbconn.conn()["permissions"].update_one(
            {"_id": member.id}, {"$set": {"permission": permission.value[1]}}, upsert=True
        )
        special_permissions[member.id] = permission.value[1]
    else:
        strip_permissions(member)


def strip_permissions(member):
    dbconn.conn()["permissions"].delete_many({"_id": member.id})
    if member.id in special_permissions:
        del special_permissions[member.id]


def load_battlebanana_permissions():
    loaded_permissions = dbconn.conn()["permissions"].find()
    for permission in loaded_permissions:
        special_permissions[permission["_id"]] = permission["permission"]


def get_special_permission(member) -> Permission:
    if member.id not in special_permissions:
        return Permission.PLAYER
    return get_permission_from_name(special_permissions[member.id])


def get_permission_from_name(permission_name: str):
    for permission in permissions:
        if permission.value[1] == permission_name:
            return permission
    return None


load_battlebanana_permissions()
