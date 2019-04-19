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


@commands.command(permission=Permission.DUEUTIL_ADMIN, args_pattern="SPB?C?")
async def createteam(ctx, name, leader, isOpen=True, lower_level=1, **details):
    """
    [CMD_KEY]createteam (name) (leader) (Minimum Level)

    Name: Team's name
    Leader: Who owns the team

    Very basic.. isn't it?
    """

    if len(name) > 32 or len(name) < 4:
        raise util.DueUtilException(ctx.channel, "Team Name must be between 4 and 32 characters")
    if name != util.filter_string(name):
        raise util.DueUtilException(ctx.channel, "Invalid team name!")
    if name.lower() in customizations.teams:
        raise util.DueUtilException(ctx.channel, "That team already exists!")
    if lower_level < 1:
        raise util.DueUtilException(ctx.channel, "Minimum level cannot be under 1!")
    if leader.team is not None:
        raise util.DueUtilException(ctx.channel, "This player is already in a team!")

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
        teams[name.lower()] = {"name": name.lower(), "owner": led_id, "admins": [led_id], "members": [led_id], "min_level": lower_level, "pendings": [], "open": isOpen}

        team_file.seek(0)
        team_file.truncate()
        json.dump(teams, team_file, indent=4, sort_keys=True)

    leader.team = name.lower()
    leader.save()
    customizations.teams._load_teams()

    await util.say(ctx.channel, "Successfully added **%s** to teams!" % name.lower())


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

    util.logger.info("%s deleted %s's team!" % (details["author"].name_clean, name.lower()))
    await util.say(ctx.channel, ":wastebasket: Team **%s** has been deleted!" % name.lower())


@commands.command(args_pattern="P", aliases=["ti"])
async def teaminvite(ctx, member, **details):
    """
    [CMD_KEY]teaminvite (player)

    NOTE: You cannot invite a player that is already in a team!
    """

    inviter = details["author"]

    if member.team is not None:
        raise util.DueUtilException(ctx.channel, "This player is already in a team!")
    if inviter.team is None:
        raise util.DueUtilException(ctx.channel, "You are not a part of a team!")
    if inviter == member:
        raise util.DueUtilException(ctx.channel, "You cannot invite yourself!")

    teams = customizations.teams
    team = teams[inviter.team]
    if not (inviter.id in team['admins']):
        raise util.DueUtilException(ctx.channel, "You do not have permissions to send invites!!")

    if inviter.team not in member.team_invites:
        member.team_invites.append(inviter.team)
    else:
        raise util.DueUtilException(ctx.channel, "This player has already been invited to your team!")
    member.save()

    await util.say(ctx.channel, ":thumbsup: All's done! Invite has been sent to **%s**!" % member.get_name_possession_clean())


@commands.command(args_pattern=None, aliases=["si"])
async def showinvites(ctx, **details):
    """
    [CMD_KEY]showinvites

    Display any team invites that you have received!
    """

    member = details["author"]

    Embed = discord.Embed(title="Displaying your team invites!", type="rich", colour=gconf.DUE_COLOUR)
    if member.team_invites is None:
        member.team_invites = []
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


@commands.command(args_pattern="C", aliases=["ai"])
async def acceptinvite(ctx, team_index, **details):
    """
    [CMD_KEY]acceptinvite (team index)

    Accept a team invite.
    """

    member = details["author"]
    team_index -= 1
    if member.team is not None:
        raise util.DueUtilException(ctx.channel, "You have not been invited to any teams.")
    if member.team_invites is None:
        member.team_invites = []
        raise util.DueUtilException(ctx.channel, "You have not been invited to any teams.")
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


@commands.command(args_pattern="C", aliases=["di"])
async def declineinvite(ctx, team_index, **details):
    """
    [CMD_KEY]declineinvite (team index)

    Decline a team invite cuz you're too good for it.
    """

    member = details["author"]
    team_index -= 1

    if member.team_invites is None:
        member.team_invites = []
    if team_index >= len(member.team_invites):
        raise util.DueUtilException(ctx.channel, "Invite not found!")
        
    team_name = member.team_invites[team_index]
    del member.team_invites[team_index]
    member.save()
            
    await util.say(ctx.channel, "Successfully deleted **%s** invite!" % team_name)


@commands.command(args_pattern=None, aliases=["mt"])
async def myteam(ctx, **details):
    """
    [CMD_KEY]myteam

    Display your team!

    Couldn't find 
    a longer description 
    for this than 
    that :shrug:
    So now it is longer
    """

    member = details["author"]
    teams = customizations.teams

    if member.team is not None:
        if member.team in teams:
            await util.say(ctx.channel, "You are a part of **%s**!" % member.team)
        else:
            member.team = None
            await util.say(ctx.channel, "You are **not** a part of a team!")
    else:
        await util.say(ctx.channel, "You are **not** a part of a team!")

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

    if member == user:
        raise util.DueUtilException(ctx.channel, "You are not allowed to promote yourself!")
    if member.team is None:
        raise util.DueUtilException(ctx.channel, "You are not in a team!")
    if user.team is None:
        raise util.DueUtilException(ctx.channel, "This player is not in a team!")
    if member.id != team["owner"]:
        raise util.DueUtilException(ctx.channel, "You are not allowed to promote users! (You must be owner!)")
    if member.team != user.team:
        raise util.DueUtilException(ctx.channel, "This player is not in your team!")
    
    with open('dueutil/game/configs/teams.json', 'r+') as team_file:
        teams = json.load(team_file)
        team = teams[member.team]
        if user.id in team["admins"]:
            raise util.DueUtilException(ctx.channel, "This user is already an admin!")

        team["admins"].append(user.id)

        team_file.seek(0)
        team_file.truncate()
        json.dump(teams, team_file, indent=4)
    
    await util.say(ctx.channel, "Successfully **promoted %s** as an **admin** in **%s**!" % (user.get_name_possession_clean(), team["name"]))


@commands.command(args_pattern="P", aliases=["du"])
async def demoteuser(ctx, user, **details):
    """
    [CMD_KEY]demoteuser (player)

    Demote an admin of your team to a normal member.

    NOTE: Only the owner can demote members!
    """

    member = details["author"]
    team = customizations.teams[member.team]

    if member.team is None:
        raise util.DueUtilException(ctx.channel, "You are not in a team!")
    if user.team is None:
        raise util.DueUtilException(ctx.channel, "This player is not in your team!")
    if member.team != user.team:
        raise util.DueUtilException(ctx.channel, "This player is not in your team!")
    if member.id != team["owner"]:
        raise util.DueUtilException(ctx.channel, "You are not allowed to demote users! (You must be the owner!)")
    if member == user:
        raise util.DueUtilException(ctx.channel, "There is no reason to demote yourself!")
    
    with open('dueutil/game/configs/teams.json', 'r+') as team_file:
        teams = json.load(team_file)
        team = teams[user.team]

        if user.id in team["admins"]:
            team["admins"].remove(user.id)
            user.save()
        else:
            raise util.DueUtilException(ctx.channel, "This player is already a member. If you meant to kick him, please use [CMD_KEY]teamkick (user)")

    await util.say(ctx.channel, "**%s** has been demoted to **Member**" % (user.get_name_possession_clean()))
        

@commands.command(args_pattern="P", aliases=["tk"])
async def teamkick(ctx, user, **details):
    """
    [CMD_KEY]teamkick (player)

    Allows you to kick a member from your team.
    You don't like him? Get rid of him!

    NOTE: Team owner & admin are able to kick users from their team!
        Admins cannot kick other admins or the owner.
        Only the owner can kick an admin.
    """

    member = details["author"]
    team = customizations.teams[member.team]

    if member == user:
        raise util.DueUtilException(ctx.channel, "There is no reason to kick yourself!")
    if member.team is None:
        raise util.DueUtilException(ctx.channel, "You are not in a team!")
    if user.team is None:
        raise util.DueUtilException(ctx.channel, "This player is not in a team!")
    if member.team != user.team:
        raise util.DueUtilException(ctx.channel, "This player is not in your team!")

    if user.id in team["admins"] and member.id != team["owner"]:
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

    await util.say(ctx.channel, "Successfully kicked **%s** from your team, adios amigos!" % user.get_name_possession())


@commands.command(args_pattern=None, aliases=["lt"])
async def leaveteam(ctx, **details):
    """
    [CMD_KEY]leaveteam

    You don't want to be in your team anymore?

    Congrats you found the right command to leave! 

    :D
    """

    user = details["author"]

    if not user.team:
        raise util.DueUtilException(ctx.channel, "You are not in any team.. You can't leave the void.. My void! :smiling_imp:")

    with open('dueutil/game/configs/teams.json', 'r+') as team_file:
        teams = json.load(team_file)
        team = teams[user.team]

        if user.id == team["owner"]:
            raise util.DueUtilException(ctx.channel, "You cannot leave this team! If you want to disband it, use `!deleteteam`")
        if user.id in team["admins"]:
            team["admins"].remove(user.id)
        team["members"].remove(user.id)
        user.team = None
        user.save()

        team_file.seek(0)
        team_file.truncate()
        json.dump(teams, team_file, indent=4)

    await util.say(ctx.channel, "You successfully left your team!")


@commands.command(args_pattern="C?", aliases=["st"])
async def showteams(ctx, page=1, **details):
    """
    [CMD_KEY]showteams (page)

    Show all existant teams
    
    Obviously they are existant...
    how would it even display something not existant?
    """
    
    page = page - 1
    if page != 0 and page * 5 >= len(customizations.teams):
        raise util.DueUtilException(ctx.channel, "Page not found")

    teamsEmbed = discord.Embed(title="There is the teams lists", description="Display all existant teams", type="rich", colour=gconf.DUE_COLOUR)
    with open('dueutil/game/configs/teams.json', 'r+') as team_file:
        teamsdict = json.load(team_file)
        teams = list(teamsdict)
        for index in range(len(teams) - 1 - (10 * page), -1, -1):
            team_name = teams[index]
            team = teamsdict[team_name]
            teamsEmbed.add_field(name=team["name"], value="Owner: **%s**\nMembers: **%s**\nRequired Level: **%s**\nRecruiting: **%s**" % (team["name"], len(team["members"]), team["min_level"], ("Yes" if team["open"] else "No")))
    
    await util.say(ctx.channel, embed=teamsEmbed)


@commands.command(args_pattern="T", aliases=["sti"])
async def showteaminfo(ctx, team, **details):
    """
    [CMD_KEY]showteaminfo (team)

    Display information about selected team - Owner, Admins, Members, team name, number of members, etc
    """

    team_embed = discord.Embed(title="Team Information", description="Displaying team information", type="rich", colour=gconf.DUE_COLOUR)
    members = ""
    admins = ""
    for id in team["admins"]:
        if id != team["owner"]:
            admins += "%s\n" % (players.find_player(id).name_clean)
    for id in team["members"]:
        if id not in team["admins"]:
            members += "%s\n" % (players.find_player(id).name_clean)

    team_embed.add_field(name="Global Information:", 
                         value="Team Name: **%s**\nMember count: **%s**\nRequired level: **%s**\nRecruiting: **%s**" % (team["name"], len(team["members"]), team["min_level"], ("Yes" if team["open"] else "No")),
                         inline=False)
    team_embed.add_field(name="Owner:", value=players.find_player(team["owner"]).name_clean)
    team_embed.add_field(name="Admins:", value=admins)
    team_embed.add_field(name="Members:", value=members)

    await util.say(ctx.channel, embed = team_embed)


@commands.command(args_pattern="T", aliases=["jt"])
async def jointeam(ctx, team, **details):
    """
    [CMD_KEY]jointeam (team)
    
    Join a team or puts you on pending list
    """

    user = details["author"]

    if user.team is not None:
        raise util.DueUtilException(ctx.channel, "You are already in a team.")
    
    with open('dueutil/game/configs/teams.json', 'r+') as team_file:
        teams = json.load(team_file)
        team = teams[team["name"]]

        if user.level <= team["min_level"]:
            raise util.DueUtilException(ctx.channel, "You must be level %s or higher to join this team!" % (str(team["min_level"])))
        if team["open"]:
            team["members"].append(user.id)
            user.team = team["name"]
            if user.id in team["pendings"]:
                team["pendings"].remove(user.id)
        else:
            if user.id in team["pendings"]:
                raise util.DueUtilException(ctx.channel, "You are already pending for that team!")
            team["pendings"].append(user.id)

        team_file.seek(0)
        team_file.truncate()
        json.dump(teams, team_file, indent=4)

    user.save()
    message = "You successfully joined **%s**!" % (team["name"])
    await util.say(ctx.channel, message if team["open"] else "You have been added to the team's pending list!")


@commands.command(args_pattern='S*', aliases=["ts"])
@commands.extras.dict_command(optional={"min level/minimum level/level": "I", "open/recruiting": "B"})
async def teamsettings(ctx, updates, **details):
    """
    [CMD_KEY]teamsettings param (value)+

    You can change both properties at the same time.

    Properties:
        __minimum level__, __recruiting__

    Example usage:

        [CMD_KEY]teamsettings "minimum level" 10

        [CMD_KEY]teamsettings recruiting true
    """

    user = details["author"]

    if user.team is None:
        raise util.DueUtilException(ctx.channel, "You are not in a team!")

    with open('dueutil/game/configs/teams.json', 'r+') as team_file:
        teams = json.load(team_file)
        team = teams[user.team]
        if user.id not in team["admins"]:
            raise util.DueUtilException(ctx.channel, "You must be an admin in order to change settings!")
        
        for prop, value in updates.items():
            if prop in ("minimum level", "level", "min level"):
                if value >= 1:
                    team["min_level"] = value
                else:
                    updates[prop] = "Must be at least 1!"
                continue
            elif prop in ("open", "recruiting"):
                team["open"] = value
            else:
                continue

        team_file.seek(0)
        team_file.truncate()
        json.dump(teams, team_file, indent=4)

    if len(updates) == 0:
        await util.say(ctx.channel, "You need to provide a valid property for the team!")
    else:
        result = "**Settings changed:**\n"
        for prop, value in updates.items():
            result += ("``%s`` → %s\n" % (prop, value))
        await util.say(ctx.channel, result)