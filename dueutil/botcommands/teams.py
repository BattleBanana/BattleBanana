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
from ..game.helpers import imagehelper
from ..permissions import Permission
from .. import commands, util, events
from ..game import customizations, awards, leaderboards, game, players, emojis

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
        leader.__setstate__({'team': None})
    
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
    customizations.teams._load_teams()

    await util.say(ctx.channel, "Successfully added %s to teams!" % name.lower())


@commands.command(persmission=Permission.DUEUTIL_ADMIN, args_pattern="S")
async def deleteteam(ctx, name, **details):
    """
    [CMD_KEY]deleteteam (team name)

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
            
            team_target = teams[teamToDelete]

            owner = players.find_player(team_target['owner'])
            owner.team = None
            owner.save()
            for admins in team_target['admins']:
                admin = players.find_player(admins)
                admin.team = None
                admin.save()
            for members in team_target['members']:
                member = players.find_player(members)
                member.team = None
                member.save()
            
            del teams[teamToDelete]
            team_file.seek(0)
            team_file.truncate()
            json.dump(teams, team_file, indent=4)
    except IOError:
        raise util.DueUtilException(ctx.channel, "Only existing team can be deleted!")

    customizations.teams._load_teams()

    await util.say(ctx.channel, ":wastebasket: Team **" + name.lower() + "** has been deleted!")
    await util.duelogger.info("**%s** deleted the **%s**'s team!" % (details["author"].name_clean, name.lower()))


@commands.command(args_pattern="P", aliases=["ti"])
async def teaminvite(ctx, member, **details):
    """
    [CMD_KEY]teaminvite (player)

    NOTE: You cannot invite a player that is already in a team!
    """

    inviter = details["author"]
    try:
        if member.team is not None:
            raise util.DueUtilException(ctx.channel, "This player is already in a team!")
    except AttributeError:
        member.__setstate__({'team': None})

    try: 
        if inviter.team is None:
            raise util.DueUtilException(ctx.channel, "You are not in any team!")
    except AttributeError:
        member.__setstate__({'team': None})
        raise util.DueUtilException(ctx.channel, "You are not in any team!")

    teams = customizations.teams
    team = teams[inviter.team]
    if not (team['owner'] == inviter.id or inviter.id in team['admins']):
        raise util.DueUtilException(ctx.channel, "You do not have permissions to send invites!!")

    try:
        if inviter.team not in member.team_invites:
            member.team_invites.append(inviter.team)
        else:
            raise util.DueUtilException(ctx.channel, "This player has already been invited to your team!")
    except AttributeError:
        member.__setstate__({'team_invites': []})
        member.team_invites.append(inviter.team)
    member.save()

    await util.say(ctx.channel, ":thumbsup: All's done! Invite has been sent to **%s**!" % member.name_clean)
    

@commands.command(args_pattern=None, aliases=["si"])
async def showinvites(ctx, **details):
    """
    [CMD_KEY]showinvites

    Display team invites you have received!
    """
    
    member = details["author"]

    Embed = discord.Embed(title="Displaying your team invites!", type="rich", colour=gconf.DUE_COLOUR)
    try:
        if member.team_invites is None:
            member.team_invites = []
    except AttributeError:
        member.__setstate__({'team_invites': []})
    
    if len(member.team_invites) == 0:
        Embed.add_field(name="No invites!", value="You do not have invites!")
    else:
        team_list=""
        i = 0
        for team_name in member.team_invites:
            if team_name in customizations.teams:
                i += 1
                team_list += ("%s- " + team_name + "\n") % i
            else:
                member.team_invites.remove(team_name)
        Embed.add_field(name="You have been invited in **%s** teams!" % len(member.team_invites), value=team_list)

    await util.say(ctx.channel, embed = Embed)


@commands.command(args_pattern="I", aliases=["AI"])
async def acceptinvite(ctx, team_index, **details):
    """
    [CMD_KEY]acceptinvite (team index)

    Accept a team invite.

    Aliases: AI
    """

    member = details["author"]
    team_index -= 1

    try:
        if member.team is not None:
            raise util.DueUtilException(ctx.channel, "This player is already in a team!")
    except AttributeError:
        member.__setstate__({'team': None})
    try:
        if member.team_invites is None:
            member.team_invites = []
            raise util.DueUtilException(ctx.channel, "You are not invited in any team! lol")
    except AttributeError:
        member.__setstate__({'team_invites': []})
        raise util.DueUtilException(ctx.channel, "You are not invited in any team! lol")
    if team_index >= len(member.team_invites):
        raise util.DueUtilException(ctx.channel, "Invite not found!")

    team_name = member.team_invites[team_index]
    with open('dueutil/game/configs/teams.json', 'r+') as team_file:
        teams = json.load(team_file)

        team_target = teams[team_name]
        team_target["members"].append(member.id)

        team_file.seek(0)
        team_file.truncate()
        json.dump(teams, team_file, indent=4)
    del member.team_invites[team_index]
            
    await util.say(ctx.channel, "Successfully joined **%s**!" % team_name)

@commands.command(args_pattern="I", aliases=["DI"])
async def declineinvite(ctx, team_index, **details):
    """
    [CMD_KEY]declineinvite (team index)

    Decline a team invite.

    Aliases: DI
    """

    member = details["author"]
    team_index -= 1

    try:
        if member.team is not None:
            raise util.DueUtilException(ctx.channel, "This player is already in a team!")
    except AttributeError:
        member.__setstate__({'team': None})
    try:
        if member.team_invites is None:
            member.team_invites = []
            raise util.DueUtilException(ctx.channel, "You are not invited in any team! lol")
    except AttributeError:
        member.__setstate__({'team_invites': []})
        raise util.DueUtilException(ctx.channel, "You are not invited in any team! lol")
    if team_index >= len(member.team_invites):
        raise util.DueUtilException(ctx.channel, "Invite not found!")
    team_name = member.team_invites[team_index]
    del member.team_invites[team_index]
            
    await util.say(ctx.channel, "Successfully deleted **%s** invite!" % team_name)