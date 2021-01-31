import jsonpickle

import discord

import generalconfig as gconf
from .. import commands, util, dbconn
from ..game import players, teams, translations


@commands.command(args_pattern="SS?B?C?")
async def createteam(ctx, name, description="This is a new and awesome team!", isOpen=True, level=1, **details):
    """team:createteam:Help"""
    owner = details["author"]
    
    if owner.team != None:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "team:createteam:AlreadyTeam"))
    if len(name) > 32 or len(name) < 4:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "team:createteam:TeamChars"))
    if len(description) > 1024:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "team:createteam:BigDesc"))
    if name != util.filter_string(name):
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "team:createteam:BadTeamName"))
    if teams.find_team(name.lower()):
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "team:createteam:TakenName"))
    if level < 1:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "team:createteam:UnderOne"))
    
    teams.Team(details["author"], name, description, level, isOpen)

    await translations.say(ctx, "team:createteam:Success", name)


@commands.command(args_pattern=None)
async def deleteteam(ctx, **details):
    """team:deleteteam:Help"""
    member = details["author"]
    
    if member.team is None:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "team:deleteteam:NoTeam"))

    team = teams.find_team(member.team)
    if team is None:
        member.team = None
    
    if member.id != team.owner:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "team:deleteteam:NotOwner"))
    
    name = team.name
    team.Delete()

    await translations.say(ctx, "team:deleteteam:Success",name)


@commands.command(args_pattern="P", aliases=["ti"])
async def teaminvite(ctx, member, **details):
    """team:teaminvite:Help"""

    inviter = details["author"]
    
    if inviter == member:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "team:teaminvite:Yourself"))

    if inviter.team is None:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "team:teaminvite:NoTeam"))

    if member.team != None:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "team:teaminvite:AlreadyInTeam"))

    team = teams.find_team(inviter.team)
    if team is None:
        inviter.team = None
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "team:teaminvite:NotInTeam"))

    if not team.isAdmin(inviter):
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "team:teaminvite:NoPerms"))

    if inviter.team in member.team_invites:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "team:teaminvite:AlreadyInvited"))
    
    member.team_invites.append(inviter.team)
    member.save()
    await translations.say(ctx, "team:teaminvite:Success", member.name)


@commands.command(args_pattern=None, aliases=["si"])
async def showinvites(ctx, **details):
    """team:showinvites:Help"""

    member = details["author"]

    Embed = discord.Embed(title=translations.translate(ctx, "team:showinvites:Title"), description=translations.translate(ctx, "team:showinvites:Desc"), type="rich", colour=gconf.DUE_COLOUR)
    if len(member.team_invites) == 0:
        Embed.add_field(name="No invites!", value="You do not have invites!")
    else:
        for id in member.team_invites:
            team = teams.find_team(id)
            if team:
                Owner = translations.translate(ctx, "other:common:Owner")
                AverageLevel = translations.translate(ctx, "other:common:AverageLvl")
                Members = translations.translate(ctx, "other:common:Members")
                RequiredLevel = translations.translate(ctx, "other:common:RequiredLvl")
                Recruiting = translations.translate(ctx, "other:common:Recruiting")
                owner = players.find_player(team.owner)
                Embed.add_field(name=team.name, 
                                value="**"+Owner+"** %s (%s)\n **"+AverageLevel+"** %s\n**"+Members+"** %s\n**"+RequiredLevel+"** %s\n**"+Recruiting+"** %s"
                                        % (owner.name, owner.id, team.avgLevel, len(team.members), team.level, (translations.translate(ctx, "other:singleword:Yes") if team.open else translations.translate(ctx, "other:singleword:No"))), 
                                inline=False)
            else:
                member.team_invites.remove(id)
    
    member.save()
    await util.reply(ctx, embed=Embed)


@commands.command(args_pattern="T", aliases=["ai"])
async def acceptinvite(ctx, team, **details):
    """team:acceptinvite:Help"""

    member = details["author"]
    
    if member.team != None:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "team:acceptinvite:AlreadyTeam"))
    if team.id not in member.team_invites:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "team:acceptinvite:InNotFound"))

    team.addMember(ctx, member)
            
    await translations.say(ctx, "team:acceptinvite:Success", team)


@commands.command(args_pattern="T", aliases=["di"])
async def declineinvite(ctx, team, **details):
    """team:declineinvite:Help"""

    member = details["author"]

    if team.id not in member.team_invites:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "team:declineinvite:NotFound"))

    member.team_invites.remove(team.id)
    member.save()
    await translations.say(ctx, "team:declineinvite:Success", team.name)


@commands.command(args_pattern=None, aliases=["mt"])
async def myteam(ctx, **details):
    """team:myteam:Help"""

    member = details["author"]
    
    team = teams.find_team(member.team)
    if team is None:
        member.team = None
    if member.team is None:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "team:myteam:NotInTeam"))
    
    team_embed = discord.Embed(title="Team Information", description="Displaying team information", type="rich", colour=gconf.DUE_COLOUR)
    pendings = ""
    members = ""
    admins = ""
    for id in team.admins:
        if id != team.owner:
            admins += "%s (%s)\n" % (players.find_player(id).name, str(id))
    for id in team.members:
        if id not in team.admins and id != team.owner:
            members += "%s (%s)\n" % (players.find_player(id).name, str(id))
    for id in team.pendings:
        if id in team.members:
            team.pendings.remove(id)
        else:
            pendings += "%s (%s)\n" % (players.find_player(id).name, str(id))
        
    team_embed.add_field(name=translations.translate(ctx, "other:common:Name"), value=team.name, inline=False)
    team_embed.add_field(name=translations.translate(ctx, "other:common:Description"), value=team.description, inline=False)
    team_embed.add_field(name=translations.translate(ctx, "other:common:Owner"), value="%s (%s)" % (players.find_player(team.owner), team.owner), inline=False)
    team_embed.add_field(name=translations.translate(ctx, "other:common:MemberCount"), value=len(team.members), inline=False)
    team_embed.add_field(name=translations.translate(ctx, "other:common:AverageLvl"), value=team.avgLevel, inline=False)
    team_embed.add_field(name=translations.translate(ctx, "other:common:RequiredLvl"), value=team.level, inline=False)
    team_embed.add_field(name=translations.translate(ctx, "other:common:Recruiting"), value=translations.translate(ctx, "other:singleworlds:Yes") if team.open else translations.translate(ctx, "other:singleworlds:No"), inline=False)
    
    if len(pendings) == 0:
        pendings = translations.translate(ctx, "team:myteam:NoPending")
    if len(members) == 0:
        members = translations.translate(ctx, "team:myteam:NoMembers")
    if len(admins) == 0:
        admins = translations.translate(ctx, "team:myteam:NoAdmins")
    
    team_embed.add_field(name=translations.translate(ctx, "other:common:Admins"), value=admins)
    team_embed.add_field(name=translations.translate(ctx, "other:common:Members"), value=members)
    team_embed.add_field(name=translations.translate(ctx, "other:common:Pendings"), value=pendings)

    await util.reply(ctx, embed=team_embed)

@commands.command(args_pattern="P", aliases=["pu"])
async def promoteuser(ctx, user, **details):
    """
    [CMD_KEY]promoteuser (player)

    Promote a member of your team to admin.
    An admin can manage the team: Invite players, kick players, etc.

    NOTE: Only the owner can promote members!
    """

    member = details["author"]

    if member == user:
        raise util.BattleBananaException(ctx.channel, "You are not allowed to promote yourself!")

    if member.team is None:
        raise util.BattleBananaException(ctx.channel, "You are not in a team!")

    if user.team is None:
        raise util.BattleBananaException(ctx.channel, "This player is not in your team!")

    if member.team != user.team:
        raise util.BattleBananaException(ctx.channel, "This player is not in your team!")

    team = teams.find_team(member.team)
    if team is None:
        member.team = None
        raise util.BattleBananaException(ctx.channel, "You are not in a team!")
    
    if member.id != team.owner:
        raise util.BattleBananaException(ctx.channel, "You are not allowed to promote users! (You must be owner!)")
    
    team.addAdmin(ctx, user)
    await util.reply(ctx, "Successfully promoted **%s** as an **admin**!" % (user.get_name_possession_clean()))


@commands.command(args_pattern="P", aliases=["du"])
async def demoteuser(ctx, user, **details):
    """
    [CMD_KEY]demoteuser (player)

    Demote an admin of your team to a normal member.

    NOTE: Only the owner can demote members!
    """

    member = details["author"]

    if member.team != user.team:
        raise util.BattleBananaException(ctx.channel, "This player is not in your team!")

    if member == user:
        raise util.BattleBananaException(ctx.channel, "There is no reason to demote yourself!")
        
    if member.team is None:
        raise util.BattleBananaException(ctx.channel, "You are not in a team!")
    
    team = teams.find_team(member.team)
    if team is None:
        member.team = None
        raise util.BattleBananaException(ctx.channel, "You are not in a team!")
    
    if member.id != team.owner:
        raise util.BattleBananaException(ctx.channel, "You are not allowed to demote users! (You must be the owner!)")
    
    if user.id not in team.admins:
        raise util.BattleBananaException(ctx.channel, "This player is already a member!")
    
    team.removeAdmin(ctx, user)
    await util.reply(ctx, "**%s** has been demoted to **Member**" % (user.name))
        

@commands.command(args_pattern="P", aliases=["tk"])
async def teamkick(ctx, user, **details):
    """team:teamkick:HELP"""

    member = details["author"]

    if member == user:
        raise util.BattleBananaException(ctx.channel, "There is no reason to kick yourself!")

    if member.team is None:
        raise util.BattleBananaException(ctx.channel, "You are not in a team!")
    
    if member.team != user.team:
        raise util.BattleBananaException(ctx.channel, "This player is not in your team!")

    team = teams.find_team(member.team)
    if team is None:
        member.team = None
        raise util.BattleBananaException(ctx.channel, "You are not in a team!")

    if not team.isAdmin(member):
        raise util.BattleBananaException(ctx.channel, "You must be an admin to use this command!")

    if team.isAdmin(user) and member.id != team.owner:
        raise util.BattleBananaException(ctx.channel, "You must be the owner to kick this player from the team!")
    
    team.Kick(ctx, user)
    await util.reply(ctx, "Successfully kicked **%s** from your team, adios amigos!" % user.name)


@commands.command(args_pattern=None, aliases=["lt"])
async def leaveteam(ctx, **details):
    """
    [CMD_KEY]leaveteam

    You don't want to be in your team anymore?

    Congrats you found the right command to leave! 

    :D
    """
    member = details["author"]

    team = teams.find_team(member.team)
    if team is None:
        member.team = None
    if member.team is None:
        raise util.BattleBananaException(ctx.channel, "You are not in any team.. You can't leave the void.. *My void!* :smiling_imp:")

    if team.owner == member.id:
        raise util.BattleBananaException(ctx.channel, "You cannot leave this team! If you want to disband it, use `%sdeleteteam`" % (details["cmd_key"]))
    
    team.Kick(ctx, member)
    await util.reply(ctx, "You successfully left your team!")


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
    if page < 0:
        raise util.BattleBananaException(ctx.channel, "Page not found!")
    
    teamsEmbed = discord.Embed(title="There is the teams lists", description="Display all existant teams", type="rich", colour=gconf.DUE_COLOUR)

    db_teams = list(dbconn.get_collection_for_object(teams.Team).find())
    top = (page * page_size + page_size)
    if page != 0 and page * 5 >= len(db_teams):
        raise util.BattleBananaException(ctx.channel, "Page not found")
    
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
            continue
    
    limit = page_size * page + page_size < len(db_teams)
    teamsEmbed.set_footer(text="%s" % (("Do %sshowteams %d for the next page!" % (details["cmd_key"], page + 2)) if limit else "That's all the teams!"))
    await util.reply(ctx, embed=teamsEmbed)


@commands.command(args_pattern="T", aliases=["sti"])
async def showteaminfo(ctx, team, **_):
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
            admins += "%s (%s)\n" % (players.find_player(id).name, str(id))
    for id in team.members:
        if id not in team.admins and id != team.owner:
            members += "%s (%s)\n" % (players.find_player(id).name, str(id))
    for id in team.pendings:
        if id in team.members:
            team.pendings.remove(id)
        else:
            pendings += "%s (%s)\n" % (players.find_player(id).name, str(id))
        
    team_embed.add_field(name="Name", value=team.name, inline=False)
    team_embed.add_field(name="Description", value=team.description, inline=False)
    team_embed.add_field(name="Owner", value="%s (%s)" % (players.find_player(team.owner).name, team.owner), inline=False)
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

    await util.reply(ctx, embed=team_embed)


@commands.command(args_pattern="T", aliases=["jt"])
async def jointeam(ctx, team, **details):
    """
    [CMD_KEY]jointeam (team)
    
    Join a team or puts you on pending list
    """

    member = details["author"]

    if member.team != None:
        raise util.BattleBananaException(ctx.channel, "You are already in a team.")

    if (team.open or team.id in member.team_invites) and member.level >= team.level:
        team.addMember(ctx, member)
        await util.reply(ctx, "You successfully joined **%s**!" % (team.name))

    elif member.level < team.level:
        raise util.BattleBananaException(ctx.channel, "You must be level %s or higher to join this team!" % (team.level))

    else:
        team.addPending(ctx, member)
        await util.reply(ctx, "You have been added to **%s** pending list!" % (team.get_name_possession()))


@commands.command(args_pattern='S*', aliases=["ts"])
@commands.extras.dict_command(optional={"min level/minimum level/level": "I", "open/recruiting": "B", "description/desc": "S"})
async def editteam(ctx, updates, **details):
    """
    [CMD_KEY]editteam param (value)+

    You can change as many properties as you want at the same time

    Properties:
        __level__, __recruiting__, __description__

    Example usage:

        [CMD_KEY]editteam "minimum level" 10

        [CMD_KEY]editteam recruiting true
    """

    member = details["author"]

    team = teams.find_team(member.team)
    if team is None:
        member.team = None
    if member.team is None:
        raise util.BattleBananaException(ctx.channel, "You are not in a team!")

    if not team.isAdmin(member):
        raise util.BattleBananaException(ctx.channel, "You need to be an admin to change settings!")
    
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
        await util.reply(ctx, "You need to provide a valid property for the team!")
    else:
        team.save()
        result = "**Settings changed:**\n"
        for prop, value in updates.items():
            result += ("``%s`` → %s\n" % (prop, value))
        await util.reply(ctx, result)


@commands.command(args_pattern="I?", aliases=["pendings", "stp"])
async def showteampendings(ctx, page=1, **details):
    """
    [CMD_KEY]showteampendings (page)

    Display a list of pending users for your team!
    """

    member = details["author"]
    page_size = 10
    page = page - 1
    team = teams.find_team(member.team)
    if page < 0:
        raise util.BattleBananaException(ctx.channel, "Page not found!")
    if team is None:
        member.Team = None
    if member.team is None:
        raise util.BattleBananaException(ctx.channel, "You're not part of any team!")
    
    top = ((page_size * page) + page_size) if ((page_size * page) + page_size < len(team.pendings)) else len(team.pendings)
    if page != 0 and page * page_size >= len(team.pendings):
        raise util.BattleBananaException(ctx.channel, "Page not found")
    
    pendings_embed = discord.Embed(title="**%s** pendings list" % (team.name), description="Displaying user pending to your team", type="rich", colour=gconf.DUE_COLOUR)
    for index in range((page_size * page), top, 1):
        id = team.pendings[index]
        member = players.find_player(id)
        pendings_embed.add_field(name=index, value="%s (%s)" % (member.name, member.id), inline=False)
            
    if len(pendings_embed.fields) == 0:
        pendings_embed.add_field(name="The list is empty!", value="Nobody is pending to your team!")
    limit = (5 * page) + 5 < len(team.pendings)
    pendings_embed.set_footer(text="%s" % (("Do %sshowpendings %d for the next page!" % (details["cmd_key"], page + 2)) if limit else "That's all the pendings!"))
    
    await util.reply(ctx, embed=pendings_embed)


@commands.command(args_pattern="P", aliases=["ap"])
async def acceptpending(ctx, user, **details):
    """
    [CMD_KEY]acceptpending (index)

    Accept a user pending to your team.
    """

    member = details["author"]
    
    team = teams.find_team(member.team)
    if team is None:
        member.team = None
    if member.team is None:
        raise util.BattleBananaException(ctx.channel, "You're not in a team!")
    if user.team != None:
        raise util.BattleBananaException(ctx.channel, "This player found his favorite team already!")
    if not team.isPending(user):
        raise util.BattleBananaException(ctx.channel, "Pending user not found!")
    
    team.addMember(ctx, user)
    await util.reply(ctx, "Accepted **%s** in your team!" % (user.name))


@commands.command(args_pattern="P", aliases=["dp"])
async def declinepending(ctx, user, **details):
    """
    [CMD_KEY]declinepending (index)

    Decline a user pending to your team.
    """

    member = details["author"]
    
    team = teams.find_team(member.team)
    if team is None:
        member.team = None
    if member.team is None:
        raise util.BattleBananaException(ctx.channel, "You're not in a team!")
    
    if not team.isPending(user):
        raise util.BattleBananaException(ctx.channel, "Pending user not found!")
    
    team.removePending(ctx, user)
    
    await util.reply(ctx, "Removed **%s** from pendings!" % (user.name))
