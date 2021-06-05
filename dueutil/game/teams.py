import jsonpickle

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

    def __init__(self, owner, name, description, level, isOpen, **details):
        self.name = name
        self.id = name.lower()
        self.description = description
        self.level = level
        self.open = isOpen
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

    def isPending(self, member):
        return member.id in self.pendings

    def isMember(self, member):
        return member.id in self.members

    def isAdmin(self, member):
        return member.id in self.admins

    def addMember(self, ctx, member):
        if self.isMember(member):
            raise util.BattleBananaException(ctx.channel, member.name + " is already a member!")

        if self.id in member.team_invites:
            member.team_invites.remove(self.id)
        self.members.append(member.id)
        self.save()

        member.team = self.id
        member.save()

    def Kick(self, ctx, member):
        if not self.isMember(member):
            raise util.BattleBananaException(ctx.channel, member.name + " is not in the team!")

        if member.id in self.admins:
            self.admins.remove(member.id)
        self.members.remove(member.id)
        self.save()

        member.team = None
        member.save()

    def addAdmin(self, ctx, member):
        if self.isAdmin(member):
            raise util.BattleBananaException(ctx.channel, member.name + " is already an admin!")

        self.admins.append(member.id)
        self.save()

    def removeAdmin(self, ctx, member):
        if not self.isAdmin(member):
            raise util.BattleBananaException(ctx.channel, member.name + " is not an admin!")

        self.admins.remove(member.id)
        self.save()

    def addPending(self, ctx, member):
        if self.isPending(member):
            raise util.BattleBananaException(ctx.channel, member.name + " is already pending!")

        self.pendings.append(member.id)
        self.save()

    def removePending(self, ctx, member):
        if not self.isPending(member):
            raise util.BattleBananaException(ctx.channel, member.name + " is not pending!")

        self.pendings.remove(member.id)
        self.save()

    def Delete(self):
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


def find_team(team_id: str) -> Team:
    if team_id in teams:
        return teams.pop(team_id)
    elif load_team(team_id):
        return teams.pop(team_id)


REFERENCE_TEAM = Team(players.REFERENCE_PLAYER, "reference team", "Okay!", 1, False, no_save=True)


def load_team(team_id):
    response = dbconn.get_collection_for_object(Team).find_one({"_id": team_id})
    if response is not None and 'data' in response:
        team_data = response['data']
        loaded_team = jsonpickle.decode(team_data)
        teams[loaded_team.id] = util.load_and_update(REFERENCE_TEAM, loaded_team)
        return True
