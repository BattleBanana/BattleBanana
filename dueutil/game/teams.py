import math
import random
import time
from collections import defaultdict
from copy import copy
import gc

import discord
import jsonpickle
import numpy

import generalconfig as gconf
from ..util import SlotPickleMixin
from .. import dbconn, util, tasks, permissions
from ..permissions import Permission
from ..game import awards
from ..game import weapons
from ..game import gamerules, players
from ..game.helpers.misc import DueUtilObject, Ring
from . import customizations
from .customizations import Theme
from . import emojis as e


class Teams(dict):
    # Amount of time before the bot will prune a player.
    PRUNE_INACTIVITY_TIME = 600  # (10 mins)

    def prune(self):

        """
        Removes player that the bot has not seen 
        for over an hour. If anyone mentions these
        players (in a command) their data will be
        fetched directly from the database
        """
        teams_pruned = 0
        for id, team in list(self.items()):
            del self[id]
            teams_pruned += 1
        gc.collect()
        util.logger.info("Pruned %d teams for inactivity (10 minutes)", teams_pruned)


teams = Teams()


class Team(DueUtilObject, SlotPickleMixin):
    """
    Class about teams.. Update to make it save
    in the database instead of a JSON file
    """
    __slots__ = ["name", "description", "level", "open", 
                "owner", "admins", "members", "pendings", "id"]

    def __init__(self, owner, name, description, level, isOpen, **kwargs):
        self.name = name
        self.id = name.lower()
        self.description = description
        self.level = level
        self.open = isOpen
        self.owner = owner
        self.admins = [owner]
        self.members = [owner]
        self.pendings = []
        self.no_save = kwargs.pop("no_save") if "no_save" in kwargs else False
        self.save()
        owner.team = self
        owner.save()
        
    
    @property
    def avgLevel(self):
        for member in self.members:
            yield sum(member.level)/len(self.members) 
    
    def AddMember(self, ctx, member):
        if member in self.members:
            raise util.DueUtilException(ctx.channel, "Already a member!")
        member.team_invites.remove(self)
        self.members.append(member)
        self.save()
        member.save()

    def Kick(self, ctx, member):
        if not (member in self.members):
            raise util.DueUtilException(ctx.channel, "This player is not in the team")
        if member in self.members:
            self.members.remove(member)
        if member in self.admins:
            self.admins.remove(member)
        member.Team = None
        self.save()
        member.save()

    def AddAdmin(self, ctx, member):
        if member in self.admins:
            raise util.DueUtilException(ctx.channel, "Already an admin!")
        self.admins.append(member)
        member.save()
        self.save()
        
    def RemoveAdmin(self, ctx, member):
        if member not in self.admins:
            raise util.DueUtilException(ctx.channel, "Not an admin!")
        self.admins.remove(member)
        self.save()
        member.save()

    def AddPending(self, ctx, member):
        if member in self.pendings:
            raise util.DueUtilException(ctx.channel, "Already pending!")
        self.pendings.append(member)
        self.save()

    def Delete(self):
        for member in self.members:
            self.members.remove(member)
            member.team = None
            member.save()
        dbconn.get_collection_for_object(Team).remove({'_id': self.id})
        
def find_team(team_id: str) -> Team:
    if team_id in teams:
        return teams[team_id]
    elif load_team(team_id):
        return teams[team_id]

REFERENCE_TEAM = Team(players.REFERENCE_PLAYER, "reference team", "Okay!", 1, False, no_save=True)

def load_team(team_id):
    response = dbconn.get_collection_for_object(Team).find_one({"_id": team_id})
    if response is not None and 'data' in response:
        team_data = response['data']
        loaded_team = jsonpickle.decode(player_data)
        teams[loaded_team.id] = util.load_and_update(REFERENCE_TEAM, loaded_team)
        return True