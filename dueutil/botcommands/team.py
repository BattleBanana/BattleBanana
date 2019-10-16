import jsonpickle
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
from .. import commands, util, events, dbconn
from ..game import customizations, awards, leaderboards, game, players, emojis, teams


@commands.command(args_pattern="SS?B?C?")
async def createteam(ctx, name, description="This is a new and awesome team!", isOpen=True, level=1, **details):
    """
    ;createteam name (description) (recruiting) (Minimum Level)

    Name: Team's name
    Description: Describe your team
    recruiting: Accepts people?
    Min level: Lowest level for someone to join the team

    Very basic.. isn't it?
    """
    owner = details["author"]
    
    if owner.team != None:
        raise util.DueUtilException(ctx.channel, "You are already in a team!")
    if len(name) > 32 or len(name) < 4:
        raise util.DueUtilException(ctx.channel, "Team Name must be between 4 and 32 characters")
    if len(description) > 1024:
        raise util.DueUtilException(ctx.channel, "Description must not exceed 1024 characters!")
    if name != util.filter_string(name):
        raise util.DueUtilException(ctx.channel, "Invalid team name!")
    if teams.find_team(name.lower()):
        raise util.DueUtilException(ctx.channel, "That team already exists!")
    if level < 1:
        raise util.DueUtilException(ctx.channel, "Minimum level cannot be under 1!")
    
    teams.Team(details["author"], name, description, level, isOpen)

    await util.say(ctx.channel, "Successfully created **%s**!" % (name))


@commands.command(args_pattern=None)
async def deleteteam(ctx, **details):
    """
    [CMD_KEY]deleteteam

    Deletes your team
    """
    member = details["author"]
    if member.team is None:
        raise util.DueUtilException(ctx.channel, "You're not in a team!")
    team = teams.find_team(member.team)
    if team is None:
        member.team = None
    if member.user_id != team.owner:
        raise util.DueUtilException(ctx.channel, "You need to be the owner to delete the team!")
    
    name = team.name
    team.Delete()

    await util.say(ctx.channel, "**%s** successfully deleted!" % (name))


@commands.command(args_pattern="P", aliases=["ti"])
async def teaminvite(ctx, member, **details):
    """
    [CMD_KEY]teaminvite (player)

    NOTE: You cannot invite a player that is already in a team!
    """

    inviter = details["author"]
    
    if inviter == member:
        raise util.DueUtilException(ctx.channel, "You cannot invite yourself!")
    if member.team != None:
        raise util.DueUtilException(ctx.channel, "This player is already in a team!")
    if inviter.team is None:
        raise util.DueUtilException(ctx.channel, "You are not a part of a team!")
    team = teams.find_team(inviter.team)
    if not team.isAdmin(inviter):
        raise util.DueUtilException(ctx.channel, "You do not have permissions to send invites!!")
    if inviter.team in member.team_invites:
        raise util.DueUtilException(ctx.channel, "This player has already been invited to join your team!")
    
    member.team_invites.append(inviter.team)
    member.save()
    await util.say(ctx.channel, ":thumbsup: Invite has been sent to **%s**!" % member.name)


@commands.command(args_pattern=None, aliases=["si"])
async def showinvites(ctx, **details):
    """
    [CMD_KEY]showinvites

    Display any team invites that you have received!
    """

    member = details["author"]

    Embed = discord.Embed(title="Displaying your team invites!", description="You were invited to join these teams!", type="rich", colour=gconf.DUE_COLOUR)
    if member.team_invites is None:
        member.team_invites = []
    if len(member.team_invites) == 0:
        Embed.add_field(name="No invites!", value="You do not have invites!")
    else:
        for id in member.team_invites:
            team = teams.find_team(id)
            if team:
                owner = players.find_player(team.owner)
                Embed.add_field(name=team.name, 
                                value="Owner: **%s** (%s)\nAverage level: **%s**\nMembers: **%s**\nRequired Level: **%s**\nRecruiting: **%s**" 
                                % (owner.name, owner.id, team.avgLevel, len(team.members), team.level, ("Yes" if team.open else "No")), 
                                inline=False)
            else:
                member.team_invites.remove(id)
    
    member.save()
    await util.say(ctx.channel, embed=Embed)


@commands.command(args_pattern="T", aliases=["ai"])
async def acceptinvite(ctx, team, **details):
    """
    [CMD_KEY]acceptinvite (team)

    Accept a team invite.
    """

    member = details["author"]
    if member.team != None:
        raise util.DueUtilException(ctx.channel, "You are already in a team.")
    if team.id not in member.team_invites:
        raise util.DueUtilException(ctx.channel, "Invite not found!")

    member.team = team.id
    team.AddMember(ctx, member)
            
    await util.say(ctx.channel, "Successfully joined **%s**!" % team)


@commands.command(args_pattern="T", aliases=["di"])
async def declineinvite(ctx, team, **details):
    """
    [CMD_KEY]declineinvite (team index)

    Decline a team invite cuz you're too good for it.
    """

    member = details["author"]

    if member.team_invites is None:
        member.team_invites = []
    if team.id not in member.team_invites:
        raise util.DueUtilException(ctx.channel, "Team not found!")

    member.team_invites.remove(team.id)
    member.save()
    await util.say(ctx.channel, "Successfully deleted **%s** invite!" % team.name)


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
    
    if member.team is None:
        raise util.DueUtilException(ctx.channel, "You're not in any team!")
    
    team = teams.find_team(member.team)
    if team is None:
        member.team = None
    team_embed = discord.Embed(title="Team Information", description="Displaying team information", type="rich", colour=gconf.DUE_COLOUR)
    pendings = ""
    members = ""
    admins = ""
    for id in team.admins:
        if id != team.owner:
            admins += "%s (%s)\n" % (players.find_player(id).name_clean, str(id))
    for id in team.members:
        if id not in team.admins and id != team.owner:
            members += "%s (%s)\n" % (players.find_player(id).name_clean, str(id))
    for id in team.pendings:
        if id in team.members:
            team.pendings.remove(id)
        else:
            pendings += "%s (%s)\n" % (players.find_player(id).name_clean, str(id))
        
    team_embed.add_field(name="Name", value=team.name, inline=False)
    team_embed.add_field(name="Description", value=team.description, inline=False)
    team_embed.add_field(name="Owner", value="%s (%s)" % (players.find_player(team.owner), team.owner), inline=False)
    team_embed.add_field(name="Member Count", value=len(team.members), inline=False)
    team_embed.add_field(name="Average level", value=team.avgLevel, inline=False)
    team_embed.add_field(name="Required level", value=team.level, inline=False)
    team_embed.add_field(name="Recruiting", value="Yes" if team.open else "No", inline=False)
    
    if len(pendings) == 0:
        pendings = "Nobody is pending!"
    if len(members) == 0:
        members = "There is no member to display!"
    if len(admins) == 0:
        admins = "There is no admin to display!"
    team_embed.add_field(name="Admins:", value=admins)
    team_embed.add_field(name="Members:", value=members)
    team_embed.add_field(name="Pendings:", value=pendings)

    await util.say(ctx.channel, embed=team_embed)

@commands.command(args_pattern="P", aliases=["pu"])
async def promoteuser(ctx, user, **details):
    """
    [CMD_KEY]promoteuser (player)

    Promote a member of your team to admin.
    Being an admin allows you to manage the team: Invite players, kick players, etc.

    NOTE: Only the owner can promote members!
    """

    member = details["author"]

    if member == user:
        raise util.DueUtilException(ctx.channel, "You are not allowed to promote yourself!")
    if member.team is None:
        raise util.DueUtilException(ctx.channel, "You are not in a team!")
    if user.team is None:
        raise util.DueUtilException(ctx.channel, "This player is not in a team!")
    team = teams.find_team(member.team)
    if team is None:
        member.team = None
    if member.id != team.owner:
        raise util.DueUtilException(ctx.channel, "You are not allowed to promote users! (You must be owner!)")
    if member.team != user.team:
        raise util.DueUtilException(ctx.channel, "This player is not in your team!")
    
    team.AddAdmin(ctx, user)
    await util.say(ctx.channel, "Successfully **promoted %s** as an **admin** in **%s**!" % (user.get_name_possession_clean(), team.name))


@commands.command(args_pattern="P", aliases=["du"])
async def demoteuser(ctx, user, **details):
    """
    [CMD_KEY]demoteuser (player)

    Demote an admin of your team to a normal member.

    NOTE: Only the owner can demote members!
    """

    member = details["author"]

    if member.team is None:
        raise util.DueUtilException(ctx.channel, "You are not in a team!")
    if member.team != user.team:
        raise util.DueUtilException(ctx.channel, "This player is not in your team!")
    
    team = teams.find_team(member.team)
    if team is None:
        member.team = None
    
    if member != team.owner:
        raise util.DueUtilException(ctx.channel, "You are not allowed to demote users! (You must be the owner!)")
    if user.user_id not in team.admins:
        raise util.DueUtilException(ctx.channel, "This player is already a member!")
    if member == user:
        raise util.DueUtilException(ctx.channel, "There is no reason to demote yourself!")
    
    team.RemoveAdmin(ctx, user)
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

    if member == user:
        raise util.DueUtilException(ctx.channel, "There is no reason to kick yourself!")
    if member.team is None:
        raise util.DueUtilException(ctx.channel, "You are not in a team!")
    if member.team != user.team:
        raise util.DueUtilException(ctx.channel, "This player is not in your team!")
    team = teams.find_team(member.team)
    if team is None:
        member.team = None
    if member.user_id not in team.admins:
        raise util.DueUtilException(ctx.channel, "You must be an admin to use this command!")
    if user.user_id in team.admins and member != team.owner:
        raise util.DueUtilException(ctx.channel, "You must be the owner to kick this player from the team!")
    
    team.Kick(ctx, user)
    await util.say(ctx.channel, "Successfully kicked **%s** from your team, adios amigos!" % user.name)


@commands.command(args_pattern=None, aliases=["lt"])
async def leaveteam(ctx, **details):
    """
    [CMD_KEY]leaveteam

    You don't want to be in your team anymore?

    Congrats you found the right command to leave! 

    :D
    """

    member = details["author"]

    if member.team is None:
        raise util.DueUtilException(ctx.channel, "You are not in any team.. You can't leave the void.. *My void!* :smiling_imp:")
    
    team = teams.find_team(member.team)
    if team is None:
        member.team = None
        
    if team.owner == member.user_id:
        raise util.DueUtilException(ctx.channel, "You cannot leave this team! If you want to disband it, use `%sdeleteteam`" % (details["cmd_key"]))
    
    team.Kick(ctx, member)
    await util.say(ctx.channel, "You successfully left your team!")


@commands.command(args_pattern="C?", aliases=["st", "teams"])
async def showteams(ctx, page=1, **details):
    """
    [CMD_KEY]showteams (page)

    Show all existant teams
    
    Obviously they are existant...
    how would it even display something not existant?
    """
    
    page_size = 5
    page = page - 1
    
    teamsEmbed = discord.Embed(title="There is the teams lists", description="Display all existant teams", type="rich", colour=gconf.DUE_COLOUR)

    db_teams = list(dbconn.get_collection_for_object(teams.Team).find())
    top = (page * page_size + page_size)
    if page != 0 and page * 5 >= len(db_teams):
        raise util.DueUtilException(ctx.channel, "Page not found")
    
    limit = top if top < len(db_teams) else len(db_teams)
    for index in range(page * page_size, limit, 1):
        #TODO: Make this team loading more efficient
        loaded_team = jsonpickle.decode(db_teams[index - 1]["data"])
        if loaded_team.id in teams.teams:
            team = teams.teams[loaded_team.id]
        else:
            teams.teams[loaded_team.id] = util.load_and_update(teams.REFERENCE_TEAM, loaded_team)
            team = teams.teams[loaded_team.id]
        try:
            owner = players.find_player(team.owner)
            teamsEmbed.add_field(name=team.name, value="Owner: **%s** (%s)\nDescription: **%s**\nMembers: **%s**\nAverage Level: **%s**\nRequired Level: **%s**\nRecruiting: **%s**" % (owner.name, owner.id, team.description, len(team.members), team.avgLevel, team.level, ("Yes" if team.open else "No")), inline=False)
        except:
            util.logging.warning("Team (%s) failed to load" % (team.name))
    
    limit = page_size * page + page_size < len(db_teams)
    teamsEmbed.set_footer(text="%s" % (("Do %sshowteams %d for the next page!" % (details["cmd_key"], page + 2)) if limit else "That's all the teams!"))
    await util.say(ctx.channel, embed=teamsEmbed)


@commands.command(args_pattern="T", aliases=["sti"])
async def showteaminfo(ctx, team, **details):
    """
    [CMD_KEY]showteaminfo (team)

    Display information about selected team - Owner, Admins, Members, team name, number of members, etc
    """

    team_embed = discord.Embed(title="Team Information", description="Displaying team information", type="rich", colour=gconf.DUE_COLOUR)
    pendings = ""
    members = ""
    admins = ""
    for id in team.admins:
        if id != team.owner:
            admins += "%s (%s)\n" % (players.find_player(id).name_clean, str(id))
    for id in team.members:
        if id not in team.admins and id != team.owner:
            members += "%s (%s)\n" % (players.find_player(id).name_clean, str(id))
    for id in team.pendings:
        if id in team.members:
            team.pendings.remove(id)
        else:
            pendings += "%s (%s)\n" % (players.find_player(id).name_clean, str(id))
        
    team_embed.add_field(name="Name", value=team.name, inline=False)
    team_embed.add_field(name="Description", value=team.description, inline=False)
    team_embed.add_field(name="Owner", value="%s (%s)" % (players.find_player(team.owner), team.owner), inline=False)
    team_embed.add_field(name="Member Count", value=len(team.members), inline=False)
    team_embed.add_field(name="Average level", value=team.avgLevel, inline=False)
    team_embed.add_field(name="Required level", value=team.level, inline=False)
    team_embed.add_field(name="Recruiting", value="Yes" if team.open else "No", inline=False)
    
    if len(pendings) == 0:
        pendings = "Nobody is pending!"
    if len(members) == 0:
        members = "There is no member to display!"
    if len(admins) == 0:
        admins = "There is no admin to display!"
    team_embed.add_field(name="Admins:", value=admins)
    team_embed.add_field(name="Members:", value=members)
    team_embed.add_field(name="Pendings:", value=pendings)

    await util.say(ctx.channel, embed=team_embed)


@commands.command(args_pattern="T", aliases=["jt"])
async def jointeam(ctx, team, **details):
    """
    [CMD_KEY]jointeam (team)
    
    Join a team or puts you on pending list
    """

    member = details["author"]

    if member.team != None:
        raise util.DueUtilException(ctx.channel, "You are already in a team.")
    
    if team.open and member.level >= team.level:
        team.AddMember(ctx, member)
        member.team = team.id
        await util.say(ctx.channel, "You successfully joined **%s**!" % (team.name))
    elif member.level < team.level:
        raise util.DueUtilException(ctx.channel, "You must be level %s or higher to join this team!" % (team.level))
    else:
        team.AddPending(ctx, member)
        await util.say(ctx.channel, "You have been added to **%s** pending list!" % (team.get_name_possession()))


@commands.command(args_pattern='S*', aliases=["ts"])
@commands.extras.dict_command(optional={"min level/minimum level/level": "I", "open/recruiting": "B", "description/desc": "S"})
async def teamsettings(ctx, updates, **details):
    """
    [CMD_KEY]teamsettings param (value)+

    You can change as many properties as you want at the same time

    Properties:
        __level__, __recruiting__, __description__

    Example usage:

        [CMD_KEY]teamsettings "minimum level" 10

        [CMD_KEY]teamsettings recruiting true
    """

    member = details["author"]

    if member.team is None:
        raise util.DueUtilException(ctx.channel, "You are not in a team!")

    team = teams.find_team(member.team)
    if team is None:
        member.team = None
    if not team.isAdmin(member):
        raise util.DueUtilException(ctx.channel, "You need to be an admin to change settings!")
    
    for prop, value in updates.items():
        if prop in ("minimum level", "level", "min level"):
            if value >= 1:
                team.level = value
            else:
                updates[prop] = "Must be at least 1!"
            continue
        elif prop in ("open", "recruiting"):
            team.open = value
        elif prop in ("description"):
            if len(value) > 1024:
                updates[prop] = "Can't be longer than 1024 characters"
            else:
                team.description = value
        else:
            continue

    if len(updates) == 0:
        await util.say(ctx.channel, "You need to provide a valid property for the team!")
    else:
        result = "**Settings changed:**\n"
        for prop, value in updates.items():
            result += ("``%s`` → %s\n" % (prop, value))
        await util.say(ctx.channel, result)


@commands.command(args_pattern="I?", aliases=["pendings", "stp"])
async def showteampendings(ctx, page=1, **details):
    """
    [CMD_KEY]showteampendings (page)

    Display a list of pending users for your team!
    """

    user = details["author"]
    page_size = 10
    page = page - 1
    if user.team is None:
        raise util.DueUtilException(ctx.channel, "You're not part of any team!")
    
    team = teams.find_team(user.team)
    pendings_embed = discord.Embed(title="**%s** pendings list" % (team.name), description="Displaying user pending to your team", type="rich", colour=gconf.DUE_COLOUR)
    
    top = ((page_size * page) + page_size) if ((page_size * page) + page_size < len(team.pendings)) else len(team.pendings)
    if page != 0 and page * page_size >= len(team.pendings):
        raise util.DueUtilException(ctx.channel, "Page not found")
    
    for index in range((page_size * page), top, 1):
        id = team.pendings[index]
        member = players.find_player(id)
        pendings_embed.add_field(name=index, value="%s (%s)" % (member.name, member.user_id), inline=False)
            
    if len(pendings_embed.fields) == 0:
        pendings_embed.add_field(name="The list is empty!", value="Nobody is pending to your team!")
    limit = (5 * page) + 5 < len(team.pendings)
    pendings_embed.set_footer(text="%s" % (("Do %sshowpendings %d for the next page!" % (details["cmd_key"], page + 2)) if limit else "That's all the pendings!"))
    
    await util.say(ctx.channel, embed=pendings_embed)


@commands.command(args_pattern="P", aliases=["ap"])
async def acceptpending(ctx, user, **details):
    """
    [CMD_KEY]acceptpending (index)

    Accept a user pending to your team.
    """

    member = details["author"]
    if member.team is None:
        raise util.DueUtilException(ctx.channel, "You're not in a team!")
    team = teams.find_team(member.team)
    if team is None:
        member.team = None
    
    if user.user_id not in team.pendings:
        raise util.DueUtilException(ctx.channel, "Pending user not found!")
    
    if user.team != None:
        raise util.DueUtilException(ctx.channel, "This player found his favorite team already!")
    
    team.AddMember(ctx, user)
    await util.say(ctx.channel, "Accepted **%s** in your team!" % (user.name_clean))


@commands.command(args_pattern="P", aliases=["dp"])
async def declinepending(ctx, user, **details):
    """
    [CMD_KEY]declinepending (index)

    Decline a user pending to your team.
    """

    member = details["author"]
    if member.team is None:
        raise util.DueUtilException(ctx.channel, "You're not in a team!")
    team = teams.find_team(member.team)
    if team is None:
        member.team = None
    
    if user.user_id not in team.pendings:
        raise util.DueUtilException(ctx.channel, "Pending user not found!")
    
    team.pendings.remove(user.user_id)
    
    await util.say(ctx.channel, "Removed **%s** from pendings!" % (user.name_clean))
    

@commands.command(args_pattern=None, permissions=Permission.DUEUTIL_OWNER)
async def atfjson(ctx, **details):
    import json
    with open('dueutil/game/configs/teams.json', 'r+') as team_file:
        teams_dict = json.load(team_file)
        for team in teams_dict:
            t1 = teams_dict[team]
            teams.Team(t1["owner"], t1["name"], "This is a new and awesome team!", t1["min_level"], t1["open"])
            t2 = teams.find_team(t1["name"])
            for member in t1["members"]:
                t2.members.append(member)
            for member in t1["admins"]:
                t2.admins.append(member)
            for member in t1["pendings"]:
                t2.pendings.append(member)
            t2.save()
            
    await util.say(ctx.channel, "Done")