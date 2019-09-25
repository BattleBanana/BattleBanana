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


class Team(DueUtilObject, SlotPickleMixin):
    """
    Class about teams.. Update to make it save
    in the database instead of a JSON file
    """
    __slots__ = ["name", "description", "level", "open", 
                "owner", "admins", "members", "pendings", "id"]

    def __init__(self, owner, name, description, level, isOpen, ctx):
        if len(name) > 32 or len(name) < 4:
            raise util.DueUtilException(ctx.channel, "Team Name must be between 4 and 32 characters")
        if name != util.filter_string(name):
            raise util.DueUtilException(ctx.channel, "Invalid team name!")
        if name in customizations.teams:
            raise util.DueUtilException(ctx.channel, "That team already exists!")
        if level < 1:
            raise util.DueUtilException(ctx.channel, "Minimum level cannot be under 1!")
        if owner.team != None:
            raise util.DueUtilException(ctx.channel, "You are already in a team!")

        self.name = name
        self.id = name.lower()
        self.description = description
        self.level = level
        self.open = isOpen
        self.owner = owner
        self.admins = [owner]
        self.members = [owner]
        self.pendings = []
        self.no_save = False
        self.save()
        owner.team = self
        owner.save()

    @property
    def members(self):
        return self.members
    
    def AddMember(self, ctx, member):
        if member.id in self.members:
            raise util.DueUtilException(ctx.channel, "Already a member!")
        self.members.append(member)

    def AddAdmin(self, ctx, member):
        if member.id in self.admins:
            raise util.DueUtilException(ctx.channel, "Already an admin!")
        self.admins.append(member)

    def AddPending(self, ctx, member):
        if member.id in self.pendings:
            raise util.DueUtilException(ctx.channel, "Already pending!")
        self.pendings.append(member)
    
    def RemoveMember(self, member):
        if member.id in self.members:
            self.members.remove(member)
        if member.id in self.admins:
            self.admins.remove(member)
        member.Team = None

    def Delete(self):
        for member in self.members:
            member.Team = None
            member.save()
        dbconn.get_collection_for_object(Team).remove({'_id': self.id})