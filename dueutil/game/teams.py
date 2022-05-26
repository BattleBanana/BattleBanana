import discord
import jsonpickle

import generalconfig as gconf

from .. import dbconn, util
from ..game import players
from ..game.helpers.misc import BattleBananaObject
from ..util import SlotPickleMixin

teams = {}


class Team(BattleBananaObject, SlotPickleMixin):
    """
    The BattleBanana Team class
    """
    __slots__ = ["name", "description", "level", "open",
                 "owner", "admins", "members", "pendings", "id"]

    def __init__(self, owner, name, description, level, is_open, **details):
        self.name = name
        self.id = name.lower()
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
    def avgLevel(self):
        level = 0
        for member in self.members:
            level += players.find_player(member).level
        return "%.2f" % (level / len(self.members))

    def is_pending(self, member):
        return member.id in self.pendings

    def is_member(self, member):
        return member.id in self.members

    def is_admin(self, member):
        return member.id in self.admins

    def add_member(self, ctx, member):
        if self.is_member(member):
            raise util.BattleBananaException(ctx.channel, member.name + " is already a member!")

        if self.id in member.team_invites:
            member.team_invites.remove(self.id)
        self.members.append(member.id)
        self.save()

        member.team = self.id
        member.save()

    def kick(self, ctx, member):
        if not self.is_member(member):
            raise util.BattleBananaException(ctx.channel, member.name + " is not in the team!")

        if member.id in self.admins:
            self.admins.remove(member.id)
        self.members.remove(member.id)
        self.save()

        member.team = None
        member.save()

    def add_admin(self, ctx, member):
        if self.is_admin(member):
            raise util.BattleBananaException(ctx.channel, member.name + " is already an admin!")

        self.admins.append(member.id)
        self.save()

    def remove_admin(self, ctx, member):
        if not self.is_admin(member):
            raise util.BattleBananaException(ctx.channel, member.name + " is not an admin!")

        self.admins.remove(member.id)
        self.save()

    def add_pending(self, ctx, member):
        if self.is_pending(member):
            raise util.BattleBananaException(ctx.channel, member.name + " is already pending!")

        self.pendings.append(member.id)
        self.save()

    def remove_pending(self, ctx, member):
        if not self.is_pending(member):
            raise util.BattleBananaException(ctx.channel, member.name + " is not pending!")

        self.pendings.remove(member.id)
        self.save()

    def delete(self):
        for member in self.members:
            member = players.find_player(member)
            member.team = None
            member.save()

        if self.id in teams:
            del teams[self.id]

        dbconn.get_collection_for_object(Team).delete_one({'_id': self.id})

    def get_name_possession(self):
        if self.name.endswith('s'):
            return self.name + "'"
        return self.name + "'s"

    def get_info_embed(self):
        pendings = ""
        members = ""
        admins = ""
        PLAYER_FORMAT = "%s (%s)\n"
        for id in self.admins:
            if id != self.owner:
                admins += PLAYER_FORMAT % (players.find_player(id).name, str(id))
        for id in self.members:
            if id not in self.admins:
                members += PLAYER_FORMAT % (players.find_player(id).name, str(id))
        for id in self.pendings:
            pendings += PLAYER_FORMAT % (players.find_player(id).name, str(id))

        if len(pendings) == 0:
            pendings = "Nobody is pending!"
        if len(members) == 0:
            members = "There is no member to display!"
        if len(admins) == 0:
            admins = "There is no admin to display!"

        owner = players.find_player(self.owner)

        team_embed = discord.Embed(title="Team Information", description="Displaying team information", type="rich",
                                    colour=gconf.DUE_COLOUR)
        team_embed.add_field(name="Name", value=self.name, inline=False)
        team_embed.add_field(name="Description", value=self.description, inline=False)
        team_embed.add_field(name="Owner", value=f"{owner.name} ({owner.id})", inline=False)
        team_embed.add_field(name="Member Count", value=len(self.members), inline=False)
        team_embed.add_field(name="Average level", value=self.avgLevel, inline=False)
        team_embed.add_field(name="Required level", value=self.level, inline=False)
        team_embed.add_field(name="Recruiting", value="Yes" if self.open else "No", inline=False)
        team_embed.add_field(name="Admins:", value=admins)
        team_embed.add_field(name="Members:", value=members)
        team_embed.add_field(name="Pendings:", value=pendings)


def find_team(team_id: str) -> Team:
    if team_id in teams:
        return teams[team_id]
    elif load_team(team_id):
        team = teams[team_id]
        team.id = team_id
        return team


REFERENCE_TEAM = Team(players.REFERENCE_PLAYER, "reference team", "Okay!", 1, False, no_save=True)


def load_team(team_id):
    response = dbconn.get_collection_for_object(Team).find_one({"_id": team_id})
    if response is not None and 'data' in response:
        team_data = response['data']
        loaded_team = jsonpickle.decode(team_data)
        teams[loaded_team.id] = util.load_and_update(REFERENCE_TEAM, loaded_team)
        return True
