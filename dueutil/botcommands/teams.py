import json
import os
import re
import subprocess
import math
import time
from io import StringIO

import discord
import objgraph

import generalconfig as gconf
import dueutil.permissions
from .. import dbconn
from ..permissions import Permission
from .. import util
from ..game import customizations

@commands.command(permission=Permission.DUEUTIL_ADMIN, args_pattern="SPI?")
async def createteam(ctx, name, leader, lower_level=1, **details):
    """
    [CMD_KEY]createteam (name) (leader) (Minimum Level)

    Name: Team's name
    Leader: Who owns the team

    Very basic.. isn't it?
    """

    if name != util.filter_string(name):
        raise util.DueUtilException(ctx.channel, "Invalid team name!")
    if name.lower() in customizations.teams:
        raise util.DueUtilException(ctx.channel, "That team already exists!")
    if lower_level < 1:
        raise util.DueUtilException(ctx.channel, "Minimum level cannot be under 1!")
    try:
        if leader.team is not None:
            raise util.DueUtilException(ctx.channel, "This player is already in a team!")
    except AttributeError:
        leader.__setstate__({'team': ""})
    
    try:
        team_file = open('dueutil/game/configs/teams.json', "r+")
    except IOError:
        team_file = open('dueutil/game/configs/teams.json', "w+")

    with team_file:
        try:
            teams = json.load(team_file)
        except ValueError:
            teams = {}

        led_id = leader.id
        teams[name.lower()] = {"name": name.lower(), "owner": led_id, "admins": [led_id], "members": [led_id], "min_level": lower_level, "pendings": []}

        team_file.seek(0)
        team_file.truncate()
        json.dump(teams, team_file, indent=4, sort_keys=True)

    leader.team = name.lower()
    leader.save()
    await util.say(ctx.channel, "Successfully added %s to teams!" % name.lower())


@commands.command(persmission=Permission.DUEUTIL_ADMIN, args_pattern="S")
async def deleteteam(ctx, name, **details):
    """
    [CMD_KEY]deleteteam (name)

    Deletes a team
    """
    teamToDelete = name.lower()
    if teamToDelete not in customizations.teams:
        raise util.DueUtilException(ctx.channel, "Team not found!")
    team = customizations.teams[teamToDelete]

    try:
        with open('dueutil/game/configs/teams.json', 'r+') as team_file:
            teams = json.load(team_file)
            if teamToDelete not in teams:
                raise util.DueUtilException(ctx.channel, "You cannot delete this team!")
            del teams[teamToDelete]
            team_file.seek(0)
            team_file.truncate()
            json.dump(backgrounds, team_file, indent=4)
    except IOError:
        raise util.DueUtilException(ctx.channel,
                                    "Only existing team can be deleted!")

    customizations.teams._load_teams()

    await util.say(ctx.channel, ":wastebasket: Team **" + name.lower() + "** has been deleted!")
    await util.duelogger.info("**%s** deleted the background **%s**" % (details["author"].name_clean, name.lower()))