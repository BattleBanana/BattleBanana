import discord
import jsonpickle

import generalconfig as gconf

from dueutil import dbconn, util
from dueutil.game import players
from dueutil.game.players import Player
from dueutil.game.helpers.misc import BattleBananaObject
from dueutil.util import SlotPickleMixin

PLAYER_FORMAT = "%s (%s)\n"

teams = {}


class Team(BattleBananaObject, SlotPickleMixin):
    """
    The BattleBanana Team class
    """

    __slots__ = ("description", "level", "open", "owner", "admins", "members", "pendings")

    def __init__(self, owner: Player, name: str, description: str, level: int, is_open: bool, **details):
        super().__init__(name.lower(), name)
        self.description = description
        self.level = level
        self.open = is_open
        self.owner = owner.id
        self.admins = [owner.id]
        self.members = [owner.id]
        self.pendings = []

        self.no_save = details.pop("no_save", False)

        self.save()
        owner.team = self.id
        owner.save()

    @property
    def average_level(self):
        level = 0
        for member in self.members:
            player = players.find_player(member)
            if player is None:
                continue

            level += player.level

        return f"{(level / len(self.members)):.2f}"

    def is_pending(self, member: Player):
        return member.id in self.pendings

    def is_member(self, member: Player):
        return member.id in self.members

    def is_admin(self, member: Player):
        return member.id in self.admins

    def add_member(self, ctx, member: Player):
        if self.is_member(member):
            raise util.BattleBananaException(ctx.channel, f"{member.name} is already a member!")

        if self.id in member.team_invites:
            member.team_invites.remove(self.id)
        self.members.append(member.id)
        self.save()

        member.team = self.id
        member.save()

    def kick(self, ctx, member: Player):
        if not self.is_member(member):
            raise util.BattleBananaException(ctx.channel, f"{member.name} is not in the team!")

        if member.id in self.admins:
            self.admins.remove(member.id)
        self.members.remove(member.id)
        self.save()

        member.team = None
        member.save()

    def add_admin(self, ctx, member: Player):
        if self.is_admin(member):
            raise util.BattleBananaException(ctx.channel, f"{member.name} is already an admin!")

        self.admins.append(member.id)
        self.save()

    def remove_admin(self, ctx, member: Player):
        if not self.is_admin(member):
            raise util.BattleBananaException(ctx.channel, f"{member.name} is not an admin!")

        self.admins.remove(member.id)
        self.save()

    def add_pending(self, ctx, member: Player):
        if self.is_pending(member):
            raise util.BattleBananaException(ctx.channel, f"{member.name} is already pending!")

        self.pendings.append(member.id)
        self.save()

    def remove_pending(self, ctx, member: Player):
        if not self.is_pending(member):
            raise util.BattleBananaException(ctx.channel, f"{member.name} is not pending!")

        self.pendings.remove(member.id)
        self.save()

    def delete(self):
        for member in self.members:
            member = players.find_player(member)
            member.team = None
            member.save()

        if self.id in teams:
            del teams[self.id]

        dbconn.get_collection_for_object(Team).delete_one({"_id": self.id})

    def get_name_possession(self):
        if self.name.endswith("s"):
            return self.name + "'"
        return self.name + "'s"

    def get_info_embed(self):
        pendings = ""
        members = ""
        admins = ""
        for id in self.admins:
            player = players.find_player(id)
            if player is None:
                continue

            if id != self.owner:
                admins += PLAYER_FORMAT % (player.name, id)

        for id in self.members:
            player = players.find_player(id)
            if player is None:
                continue

            if id not in self.admins:
                members += PLAYER_FORMAT % (player.name, str(id))

        for id in self.pendings:
            player = players.find_player(id)
            if player is None:
                continue

            pendings += PLAYER_FORMAT % (player.name, str(id))

        if len(pendings) == 0:
            pendings = "Nobody is pending!"
        if len(members) == 0:
            members = "There is no member to display!"
        if len(admins) == 0:
            admins = "There is no admin to display!"

        owner = players.find_player(self.owner)

        embed = discord.Embed(
            title="Team Information", description="Displaying team information", type="rich", colour=gconf.DUE_COLOUR
        )
        embed.add_field(name="Name", value=self.name, inline=False)
        embed.add_field(name="Description", value=self.description, inline=False)
        embed.add_field(name="Owner", value=f"{owner.name} ({owner.id})", inline=False)
        embed.add_field(name="Member Count", value=len(self.members), inline=False)
        embed.add_field(name="Average level", value=self.average_level, inline=False)
        embed.add_field(name="Required level", value=self.level, inline=False)
        embed.add_field(name="Recruiting", value="Yes" if self.open else "No", inline=False)
        embed.add_field(name="Admins:", value=admins)
        embed.add_field(name="Members:", value=members)
        embed.add_field(name="Pendings:", value=pendings)

        return embed


def find_team(team_id: str) -> Team | None:
    if team_id in teams:
        return teams[team_id]
    return load_team(team_id)


REFERENCE_TEAM = Team(players.REFERENCE_PLAYER, "reference team", "Okay!", 1, False, no_save=True)


def load_team(team_id: int) -> Team | None:
    response = dbconn.get_collection_for_object(Team).find_one({"_id": team_id})
    if response is not None and "data" in response:
        team_data = response["data"]
        loaded_team: Team = jsonpickle.decode(team_data)
        teams[loaded_team.id] = loaded_team
        return loaded_team
