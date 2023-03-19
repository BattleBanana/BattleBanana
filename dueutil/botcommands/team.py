import discord
import jsonpickle

import generalconfig as gconf

from .. import commands, dbconn, util
from ..game import players, teams

NOT_IN_TEAM = "You are not in a team!"
ALREADY_IN_TEAM = "You are already in a team!"
NOT_IN_YOUR_TEAM = "This player is not in your team!"


def in_a_team(player: players.Player):
    """
    Checks if the player is in a team.
    :param player: The player to check.
    :return: True if the player is in a team, False otherwise.
    """
    if player.team is None:
        return False

    team = teams.find_team(player.team)
    if team is None:
        player.team = None
        player.save()

    return player.team is not None


@commands.command(args_pattern="SS?B?C?")
async def createteam(ctx, name, description="This is a new and awesome team!", is_open=True, level=1, **details):
    """
    [CMD_KEY]createteam name (description) (recruiting) (Minimum Level)

    Name: Team's name
    Description: Describe your team
    recruiting: Accepts people?
    Min level: Lowest level for someone to join the team
    """
    owner = details["author"]

    if in_a_team(owner):
        raise util.BattleBananaException(ctx.channel, ALREADY_IN_TEAM)

    if len(name) > 32 or len(name) < 4:
        raise util.BattleBananaException(ctx.channel, "Team Name must be between 4 and 32 characters")

    if len(description) > 1024:
        raise util.BattleBananaException(ctx.channel, "Description must not exceed 1024 characters!")

    if name != util.filter_string(name):
        raise util.BattleBananaException(ctx.channel, "Invalid team name!")

    if teams.find_team(name.lower()):
        raise util.BattleBananaException(ctx.channel, "That team already exists!")

    if level < 1:
        raise util.BattleBananaException(ctx.channel, "Minimum level cannot be under 1!")

    teams.Team(owner, name, description, level, is_open)

    await util.reply(ctx, f"Successfully created **{name}**!")


@commands.command(args_pattern=None)
async def deleteteam(ctx, **details):
    """
    [CMD_KEY]deleteteam

    Delete your team
    """
    player = details["author"]

    if not in_a_team(player):
        raise util.BattleBananaException(ctx.channel, NOT_IN_TEAM)

    team = teams.find_team(player.team)
    if player.id != team.owner:
        raise util.BattleBananaException(ctx.channel, "You need to be the owner to delete the team!")

    name = team.name
    team.delete()

    await util.reply(ctx, f"**{name}** successfully deleted!")


@commands.command(args_pattern="P", aliases=["ti"])
async def teaminvite(ctx, member, **details):
    """
    [CMD_KEY]teaminvite (player)

    Invite a player to your team

    NOTE: You cannot invite a player that is already in a team!
    """

    player = details["author"]

    if player == member:
        raise util.BattleBananaException(ctx.channel, "You cannot invite yourself!")

    if not in_a_team(player):
        raise util.BattleBananaException(ctx.channel, NOT_IN_TEAM)

    if in_a_team(member):
        raise util.BattleBananaException(ctx.channel, "This player is already in a team!")

    team = teams.find_team(player.team)
    if not team.is_admin(player):
        raise util.BattleBananaException(ctx.channel, "You do not have permissions to send invites!")

    if player.team in member.team_invites:
        raise util.BattleBananaException(ctx.channel, "This player has already been invited to join your team!")

    member.team_invites.append(player.team)
    member.save()
    await util.reply(ctx, f":thumbsup: Invite has been sent to **{member.name}**!")


@commands.command(args_pattern=None, aliases=["si"])
async def showinvites(ctx, **details):
    """
    [CMD_KEY]showinvites

    Show all your team invites
    """

    player = details["author"]

    invites_embed = discord.Embed(
        title="Displaying your team invites!",
        description="You were invited to join these teams!",
        type="rich",
        colour=gconf.DUE_COLOUR,
    )
    if len(player.team_invites) == 0:
        invites_embed.add_field(name="No invites!", value="You do not have invites!")
    else:
        for id in player.team_invites:
            team = teams.find_team(id)
            if team:
                owner = players.find_player(team.owner)
                invites_embed.add_field(
                    name=team.name,
                    value=(
                        f"**Owner:** {owner.name} ({owner.id})\n"
                        + f"**Average level:** {team.avgLevel}\n"
                        + f"**Members:** {len(team.members)}\n"
                        + f"**Required Level:** {team.level}\n"
                        + f"**Recruiting:** {'Yes' if team.open else 'No'}"
                    ),
                    inline=False,
                )
            else:
                player.team_invites.remove(id)

    player.save()
    await util.reply(ctx, embed=invites_embed)


@commands.command(args_pattern="T", aliases=["ai"])
async def acceptinvite(ctx, team, **details):
    """
    [CMD_KEY]acceptinvite (team)

    Accept a team invite
    """

    player = details["author"]

    if in_a_team(player):
        raise util.BattleBananaException(ctx.channel, ALREADY_IN_TEAM)

    if team.id not in player.team_invites:
        raise util.BattleBananaException(ctx.channel, "Invite not found!")

    team.add_member(ctx, player)

    await util.reply(ctx, f"Successfully joined **{team}**!")


@commands.command(args_pattern="T", aliases=["di"])
async def declineinvite(ctx, team, **details):
    """
    [CMD_KEY]declineinvite (team index)

    Decline a team invite cuz you're too good for it :sunglasses:
    """

    player = details["author"]

    if team.id not in player.team_invites:
        raise util.BattleBananaException(ctx.channel, "Team not found!")

    player.team_invites.remove(team.id)
    player.save()
    await util.reply(ctx, f"Successfully deleted **{team.name}** invite!")


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

    player = details["author"]

    if not in_a_team(player):
        raise util.BattleBananaException(ctx.channel, NOT_IN_TEAM)

    team = teams.find_team(player.team)

    await util.reply(ctx, embed=team.get_info_embed())


@commands.command(args_pattern="P", aliases=["pu"])
async def promoteuser(ctx, target, **details):
    """
    [CMD_KEY]promoteuser (player)

    Promote a member of your team to admin.
    An admin can invite and kick players from the team.

    NOTE: Only the owner can promote members!
    """

    player = details["author"]

    if player == target:
        raise util.BattleBananaException(ctx.channel, "You are not allowed to promote yourself!")

    if not in_a_team(player):
        raise util.BattleBananaException(ctx.channel, NOT_IN_TEAM)

    if target.team != player.team:
        raise util.BattleBananaException(ctx.channel, NOT_IN_YOUR_TEAM)

    team = teams.find_team(player.team)
    if player.id != team.owner:
        raise util.BattleBananaException(ctx.channel, "You are not allowed to promote users! (You must be owner!)")

    team.add_admin(ctx, target)
    await util.reply(ctx, f"Successfully promoted **{target.get_name_possession_clean()}** as an **admin**!")


@commands.command(args_pattern="P", aliases=["du"])
async def demoteuser(ctx, target, **details):
    """
    [CMD_KEY]demoteuser (player)

    Demote an admin of your team to a normal member.

    NOTE: Only the owner can demote members!
    """

    player = details["author"]

    if player == target:
        raise util.BattleBananaException(ctx.channel, "There is no reason to demote yourself!")

    if not in_a_team(player):
        raise util.BattleBananaException(ctx.channel, NOT_IN_TEAM)

    if target.team != player.team:
        raise util.BattleBananaException(ctx.channel, NOT_IN_YOUR_TEAM)

    team = teams.find_team(player.team)
    if player.id != team.owner:
        raise util.BattleBananaException(ctx.channel, "You are not allowed to demote members! (You must be the owner!)")

    if target.id not in team.admins:
        raise util.BattleBananaException(ctx.channel, "This player is already a member!")

    team.remove_admin(ctx, target)
    await util.reply(ctx, f"**{target.name}** has been demoted to **Member**")


@commands.command(args_pattern="P", aliases=["tk"])
async def teamkick(ctx, target, **details):
    """
    [CMD_KEY]teamkick (player)

    Allows you to kick a member from your team.
    You don't like him? Get rid of him!

    NOTE: Team owner & admin are able to kick users from their team!
        Admins cannot kick other admins or the owner.
        Only the owner can kick an admin.
    """

    player = details["author"]

    if player == target:
        raise util.BattleBananaException(ctx.channel, "There is no reason to kick yourself!")

    if not in_a_team(player):
        raise util.BattleBananaException(ctx.channel, NOT_IN_TEAM)

    if not in_a_team(target) or target.team != player.team:
        raise util.BattleBananaException(ctx.channel, NOT_IN_YOUR_TEAM)

    team = teams.find_team(player.team)
    if not team.is_admin(player):
        raise util.BattleBananaException(ctx.channel, "You must be an admin to use this command!")

    if team.is_admin(target) and player.id != team.owner:
        raise util.BattleBananaException(ctx.channel, "You must be the owner to kick this player from the team!")

    team.kick(ctx, target)
    await util.reply(ctx, f"Successfully kicked **{target.name}** from your team, adios amigos!")


@commands.command(args_pattern=None, aliases=["lt"])
async def leaveteam(ctx, **details):
    """
    [CMD_KEY]leaveteam

    You don't want to be in your team anymore?

    Congrats you found the right command to leave!

    NOTE: You can't leave a team if you are the owner!
    """
    player = details["author"]

    if not in_a_team(player):
        raise util.BattleBananaException(
            ctx.channel, "You are not in any team.. You can't leave the void.. *My void!* :smiling_imp:"
        )

    team = teams.find_team(player.team)
    if team.owner == player.id:
        raise util.BattleBananaException(
            ctx.channel,
            f"You cannot leave this team! If you want to disband it, use `{details['cmd_key']}deleteteam`",
        )

    team.kick(ctx, player)
    await util.reply(ctx, "You successfully left your team!")


@commands.command(args_pattern="C?", aliases=["st", "teams"])
async def showteams(ctx, page=1, **details):
    """
    [CMD_KEY]showteams (page)

    Display all teams!
    """

    page_size = 5
    page = page - 1
    if page < 0:
        raise util.BattleBananaException(ctx.channel, "Page not found!")

    teams_embed = discord.Embed(
        title="There is the teams lists", description="Display all existant teams", type="rich", colour=gconf.DUE_COLOUR
    )

    db_teams = list(dbconn.get_collection_for_object(teams.Team).find())
    top = page * page_size + page_size
    if page != 0 and page * 5 >= len(db_teams):
        raise util.BattleBananaException(ctx.channel, "Page not found")

    limit = top if top < len(db_teams) else len(db_teams)
    for index in range(page * page_size, limit, 1):
        # TODO: Make this team loading more efficient
        loaded_team = jsonpickle.decode(db_teams[index - 1]["data"])
        if loaded_team.id in teams.teams:
            team = teams.teams[loaded_team.id]
        else:
            teams.teams[loaded_team.id] = util.load_and_update(teams.REFERENCE_TEAM, loaded_team)
            team = teams.teams[loaded_team.id]

        owner = players.find_player(team.owner)
        teams_embed.add_field(
            name=team.name,
            value=(
                f"Owner: **{owner.name}** ({owner.id})\n"
                + f"Description: **{team.description}**\n"
                + f"Members: **{len(team.members)}**\n"
                + f"Average Level: **{team.avgLevel}**\n"
                + f"Required Level: **{team.level}**\n"
                + f"Recruiting: **{'Yes' if team.open else 'No'}**"
            ),
            inline=False,
        )

    limit = page_size * page + page_size < len(db_teams)
    teams_embed.set_footer(
        text=f"Do {details['cmd_key']}showteams {page + 2} for the next page!" if limit else "That's all the teams!"
    )
    await util.reply(ctx, embed=teams_embed)


@commands.command(args_pattern="T", aliases=["sti"])
async def showteaminfo(ctx, team, **_):
    """
    [CMD_KEY]showteaminfo (team)

    Display information about a team!
    """

    await util.reply(ctx, embed=team.get_info_embed())


@commands.command(args_pattern="T", aliases=["jt"])
async def jointeam(ctx, team, **details):
    """
    [CMD_KEY]jointeam (team)

    Join a team or the pending list
    """

    player = details["author"]

    if in_a_team(player):
        raise util.BattleBananaException(ctx.channel, ALREADY_IN_TEAM)

    if (team.open or team.id in player.team_invites) and player.level >= team.level:
        team.add_member(ctx, player)
        await util.reply(ctx, f"You successfully joined **{team.name}**!")

    elif player.level < team.level:
        raise util.BattleBananaException(ctx.channel, f"You must be level {team.level} or higher to join this team!")

    else:
        team.add_pending(ctx, player)
        await util.reply(ctx, f"You have been added to **{team.get_name_possession()}** pending list!")


@commands.command(args_pattern="S*", aliases=["ts"])
@commands.extras.dict_command(
    optional={"min level/minimum level/level": "I", "open/recruiting": "B", "description/desc": "S"}
)
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

    player = details["author"]

    if not in_a_team(player):
        raise util.BattleBananaException(ctx.channel, NOT_IN_TEAM)

    team = teams.find_team(player.team)
    if not team.is_admin(player):
        raise util.BattleBananaException(ctx.channel, "You need to be an admin to change settings!")

    for prop, value in updates.items():
        if prop in ("minimum level", "level", "min level"):
            if value >= 1:
                team.level = value
            else:
                updates[prop] = "Must be at least 1!"
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
            result += f"``{prop}`` → {value}\n"

        await util.reply(ctx, result)


@commands.command(args_pattern="I?", aliases=["pendings", "showteampendings"])
async def showpendings(ctx, page=1, **details):
    """
    [CMD_KEY]showpendings (page)

    Display a list of pending users for your team!
    """

    player = details["author"]
    page_size = 10
    page = page - 1

    if not in_a_team(player):
        raise util.BattleBananaException(ctx.channel, NOT_IN_TEAM)

    if page < 0:
        raise util.BattleBananaException(ctx.channel, "Page not found!")

    team = teams.find_team(player.team)
    top = (
        ((page_size * page) + page_size)
        if ((page_size * page) + page_size < len(team.pendings))
        else len(team.pendings)
    )
    if page != 0 and page * page_size >= len(team.pendings):
        raise util.BattleBananaException(ctx.channel, "Page not found")

    pendings_embed = discord.Embed(
        title=f"**{team.name}** pendings list" % (),
        description="Displaying players pending to your team",
        type="rich",
        colour=gconf.DUE_COLOUR,
    )
    for index in range((page_size * page), top, 1):
        pending_id = team.pendings[index]
        player = players.find_player(pending_id)
        pendings_embed.add_field(name=index, value=f"{player.name} ({player.id})", inline=False)

    if len(pendings_embed.fields) == 0:
        pendings_embed.add_field(name="The list is empty!", value="Nobody is pending to your team!")

    limit = (5 * page) + 5 < len(team.pendings)
    pendings_embed.set_footer(
        text=(
            f"Do {details['cmd_key']}showpendings {page + 2} for the next page!"
            if limit
            else "That's all the pendings!"
        )
    )

    await util.reply(ctx, embed=pendings_embed)


@commands.command(args_pattern="P", aliases=["ap"])
async def acceptpending(ctx, target, **details):
    """
    [CMD_KEY]acceptpending (index)

    Accept a player pending to your team.
    """

    player = details["author"]

    if not in_a_team(player):
        raise util.BattleBananaException(ctx.channel, NOT_IN_TEAM)

    if in_a_team(target):
        raise util.BattleBananaException(ctx.channel, "This player found his favorite team already!")

    team = teams.find_team(player.team)
    if not team.is_pending(target):
        raise util.BattleBananaException(ctx.channel, "Pending player not found!")

    team.add_member(ctx, target)
    await util.reply(ctx, f"Accepted **{target.name}** in your team!")


@commands.command(args_pattern="P", aliases=["dp"])
async def declinepending(ctx, target, **details):
    """
    [CMD_KEY]declinepending (index)

    Decline a player pending to your team.
    """

    player = details["author"]

    if not in_a_team(player):
        raise util.BattleBananaException(ctx.channel, NOT_IN_TEAM)

    team = teams.find_team(player.team)
    if not team.is_pending(target):
        raise util.BattleBananaException(ctx.channel, "Pending player not found!")

    team.remove_pending(ctx, target)

    await util.reply(ctx, f"Removed **{target.name}** from pendings!")
