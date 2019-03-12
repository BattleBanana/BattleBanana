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
    
    member.save()
    await util.say(ctx.channel, embed = Embed)


@commands.command(args_pattern="I", aliases=["ai"])
async def acceptinvite(ctx, team_index, **details):
    """
    [CMD_KEY]acceptinvite (team index)

    Accept a team invite.
    """

    member = details["author"]
    team_index -= 1

    try:
        if member.team is not None:
            raise util.DueUtilException(ctx.channel, "You are already in a team!")
    except AttributeError:
        member.__setstate__({'team': None})
    try:
        if member.team_invites is None:
            member.team_invites = []
            raise util.DueUtilException(ctx.channel, "You are not invited in any team!")
    except AttributeError:
        member.__setstate__({'team_invites': []})
        raise util.DueUtilException(ctx.channel, "You are not invited in any team!")
    if team_index >= len(member.team_invites):
        raise util.DueUtilException(ctx.channel, "Invite not found!")

    teams = customizations.teams
    team_name = member.team_invites[team_index]
    member.team = team_name
    with open('dueutil/game/configs/teams.json', 'r+') as team_file:
        teams = json.load(team_file)
        if not (team_name in teams):
            del member.team_invites[team_index]
            member.save()
            raise util.DueUtilException(ctx.channel, "This team does not exist anymore!")

        team_target = teams[team_name]
        team_target["members"].append(member.id)

        team_file.seek(0)
        team_file.truncate()
        json.dump(teams, team_file, indent=4)
    del member.team_invites[team_index]
    member.save()
            
    await util.say(ctx.channel, "Successfully joined **%s**!" % team_name)


@commands.command(args_pattern="I", aliases=["di"])
async def declineinvite(ctx, team_index, **details):
    """
    [CMD_KEY]declineinvite (team index)

    Decline a team invite.
    """

    member = details["author"]
    team_index -= 1

    try:
        if member.team_invites is None:
            member.team_invites = []
    except AttributeError:
        member.__setstate__({'team_invites': []})
    if team_index >= len(member.team_invites):
        raise util.DueUtilException(ctx.channel, "Invite not found!")
        
    team_name = member.team_invites[team_index]
    del member.team_invites[team_index]
    member.save()
            
    await util.say(ctx.channel, "Successfully deleted **%s** invite!" % team_name)


@commands.command(args_pattern=None, aliases=["mt"])
async def myteam(ctx, **details):
    """
    [CMD_KEY]teams

    Display your team!

    Couldn't find 
    a longer description 
    for this than 
    that :shrug:
    So now it is longer
    """

    member = details["author"]
    teams = customizations.teams

    try:
        if member.team is not None:
            if member.team in teams:
                await util.say(ctx.channel, "You are appart **%s**!" % member.team)
            else:
                member.team = None
                await util.say(ctx.channel, "You are **not** appart a team!")
        else:
            await util.say(ctx.channel, "You are **not** appart a team!")
    except AttributeError:
        member.__setstate__({'team': None})
        await util.say(ctx.channel, "You are **not** appart a team!")

    member.save()

@commands.command(args_pattern="P", aliases=["pu"])
async def promoteuser(ctx, user, **details):
    """
    [CMD_KEY]promoteuser (player)

    Promote a member of your team to admin.
    Being an admin allows you to manage the team: Invite players, kick players, etc.

    NOTE: Only the owner can promote members!
    """

    member = details["author"]
    team = customizations.teams[member.team]

    try:
        if member.team is None:
            raise util.DueUtilException(ctx.channel, "You are not in a team!")
    except AttributeError:
        member.__setstate__({'team': None})
        raise util.DueUtilException(ctx.channel, "You are not in a team!")
    try:
        if user.team is None:
            raise util.DueUtilException(ctx.channel, "This player is not in a team!")
    except AttributeError:
        member.__setstate__({'team': None})
        raise util.DueUtilException(ctx.channel, "This player is not in a team!")
    if not(member.id == team["owner"]):
        raise util.DueUtilException(ctx.channel, "You are not allowed to promote users! (You must be owner!)")
    if not (member.team == user.team):
        raise util.DueUtilException(ctx.channel, "This player is not in your team, therefore, you cannot take actions on him!")
    if member.id == user.id:
        raise util.DueUtilException(ctx.channel, "You are not allowed to promote yourself!")
    
    with open('dueutil/game/configs/teams.json', 'r+') as team_file:
        teams = json.load(team_file)
        team = teams[member.team]
        if user.id in team["admins"]:
            raise util.DueUtilException(ctx.channel, "This user is already an admin!")

        team["admins"].append(user.id)

        team_file.seek(0)
        team_file.truncate()
        json.dump(teams, team_file, indent=4)
    
    await util.say(ctx.channel, "Successfully **promoted %s** as an **admin** in **%s**!" % (user.name, team["name"]))


@commands.command(args_pattern="P", aliases=["tk"])
async def teamkick(ctx, user, **details):
    """
    [CMD_KEY]teamkick (player)

    Allows you to kick a member from your team.
    You don't like him? Get ride of him!

    NOTE: Team owner & admin are able to kick users from their team!
        Admins cannot kick other admins or the owner.
        Only the owner can kick an admin.
    """

    member = details["author"]
    team = customizations.teams[member.team]

    if member == user:
        raise util.DueUtilException(ctx.channel, "There is no reason to kick yourself!")
    try:
        if member.team is None:
            raise util.DueUtilException(ctx.channel, "You are not in a team!")
    except AttributeError:
        member.__setstate__({'team': None})
        raise util.DueUtilException(ctx.channel, "You are not in a team!")
    
    try:
        if user.team is None:
            raise util.DueUtilException(ctx.channel, "This player is not in a team!")
        if not (member.team == user.team):
            raise util.DueUtilException(ctx.channel, "This player is not in your team!")
    except AttributeError:
        member.__setstate__({'team': None})
        raise util.DueUtilException(ctx.channel, "This player is not in your team!")

    if user.id in team["admins"] and not (member.id == team["owner"]):
        raise util.DueUtilException(ctx.channel, "You must be the owner to kick this player from the team!")
    if member.id not in team["admins"]:
        raise util.DueUtilException(ctx.channel, "You must be an admin to use this command!")
    
    with open('dueutil/game/configs/teams.json', 'r+') as team_file:
        teams = json.load(team_file)
        team = teams[member.team]

        user.team = None
        if user.id in team["members"]:
            team["members"].remove(user.id)
        if user.id in team["admins"]:
            team["admins"].remove(user.id)

        team_file.seek(0)
        team_file.truncate()
        json.dump(teams, team_file, indent=4)

    await util.say(ctx.channel, "Successfully kicked **%s** from your team, adios amigos!" % user.name)