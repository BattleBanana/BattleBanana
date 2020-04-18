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
from ..game.helpers.misc import BattleBananaObject, Ring
from . import customizations
from .customizations import Theme
from . import emojis as e


teams = {}

class Team(BattleBananaObject, SlotPickleMixin):
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
        self.owner = owner.user_id
        self.admins = [owner.user_id]
        self.members = [owner.user_id]
        self.pendings = []
        
        self.no_save = kwargs.pop("no_save") if "no_save" in kwargs else False
        
        owner.team = self.id
        self.save()
        owner.save()
        
    
    @property
    def avgLevel(self):
        level = 0
        for member in self.members:
            level += players.find_player(member).level
        return "%.2f" % (level/len(self.members))
    
    def isMember(self, member):
        return member.id in self.members
    
    def isAdmin(self, member):
        return member.id in self.admins
    
    def AddMember(self, ctx, member):
        if member.user_id in self.members:
            raise util.BattleBananaException(ctx.channel, "Already a member!")
        
        if self.id in member.team_invites:
            member.team_invites.remove(self.id)
        member.team = self.id
        self.members.append(member.user_id)
        self.save()
        member.save()

    def Kick(self, ctx, member):
        if not (member.user_id in self.members):
            raise util.BattleBananaException(ctx.channel, "This player is not in the team")
        
        if member.user_id in self.members:
            self.members.remove(member.user_id)
        if member.user_id in self.admins:
            self.admins.remove(member.user_id)
        member.team = None
        self.save()
        member.save()

    def AddAdmin(self, ctx, member):
        if member.user_id in self.admins:
            raise util.BattleBananaException(ctx.channel, "Already an admin!")
        
        self.admins.append(member.user_id)
        self.save()
        member.save()
        
    def RemoveAdmin(self, ctx, member):
        if member.user_id not in self.admins:
            raise util.BattleBananaException(ctx.channel, "Not an admin!")
        
        self.admins.remove(member.user_id)
        self.save()
        member.save()

    def AddPending(self, ctx, member):
        if member.user_id in self.pendings:
            raise util.BattleBananaException(ctx.channel, "Already pending!")
        
        self.pendings.append(member.user_id)
        self.save()
        
    def RemovePending(self, ctx, member):
        if not (member.user_id in self.pendings):
            raise util.BattleBananaException(ctx.channel, "Not pending!")
        
        self.pendings.remove(member.user_id)
        self.save()

    def Delete(self):
        for member in self.members:
            member = players.find_player(member)
            member.team = None
            member.save()
        if self.id in teams:
            del teams[self.id]
        self.save()
        dbconn.get_collection_for_object(Team).remove({'_id': self.id})
        
    def get_name_possession(self):
        if self.name.endswith('s'):
            return self.name + "'"
        return self.name + "'s"
        
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
        loaded_team = jsonpickle.decode(team_data)
        teams[loaded_team.id] = util.load_and_update(REFERENCE_TEAM, loaded_team)
        return True