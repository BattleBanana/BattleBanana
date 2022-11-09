import discord

import generalconfig as gconf
from .. import util, commands
from ..permissions import Permission


BUG_REPORT = "Bug report"
SUGGESTION = "Suggestion"


class FeedbackHandler:
    """
    Another weird class to make something easier.
    """

    def __init__(self, **options):
        self.channel = options.get('channel')
        self.type = options.get('type').lower()
        self.trello_list = options.get('trello_list')

    async def send_report(self, ctx, message):
        author = ctx.author
        author_name = str(author)

        trello_link = await util.trello_client.add_card(board_url=gconf.trello_board,
                                                        name=message,
                                                        desc=("Automated %s added by BattleBanana\n" % self.type
                                                              + "Author: %s (id %s)" % (author_name, author.id)),
                                                        list_name=self.trello_list,
                                                        labels=["automated",
                                                                "Bug" if self.type == BUG_REPORT else SUGGESTION])
        author_icon_url = author.display_avatar.url
        if author_icon_url == "":
            author_icon_url = author.display_avatar.url
        report = discord.Embed(color=gconf.DUE_COLOUR)
        report.set_author(name=author_name, icon_url=author_icon_url)
        report.add_field(name=self.type.title(), value="%s\n\n[Trello card](%s)" % (message, trello_link), inline=False)
        report.add_field(name=ctx.guild.name, value=ctx.guild.id)
        report.add_field(name=ctx.channel.name, value=ctx.channel.id)
        report.set_footer(text="Sent at " + util.pretty_time())
        await util.reply(ctx,
                         ":mailbox_with_mail: Sent! You can view your %s here: <%s>" % (self.type, trello_link))
        await util.reply(ctx, embed=report)

        log_report = discord.Embed(color=gconf.DUE_COLOUR)
        log_report.set_author(name=author_name, icon_url=author_icon_url)
        log_report.add_field(name=self.type.title(), value="%s\n\n[Trello card](%s)" % (message, trello_link),
                            inline=False)
        log_report.add_field(name=ctx.guild.name, value=ctx.guild.id)
        log_report.add_field(name="author", value=ctx.author.id)
        log_report.set_footer(text="Received at " + util.pretty_time())
        await util.say(gconf.bug_channel if self.type == BUG_REPORT else gconf.feedback_channel, embed=log_report)


bug_reporter = FeedbackHandler(channel=gconf.bug_channel, type=BUG_REPORT, trello_list="bugs")
suggestion_sender = FeedbackHandler(channel=gconf.feedback_channel, type=SUGGESTION, trello_list="suggestions")


@commands.command(permission=Permission.DISCORD_USER, args_pattern="S")
@commands.ratelimit(cooldown=300, error=":cold_sweat: Please don't submit anymore reports (for a few minutes)!")
async def bugreport(ctx, report, **_):
    """
    [CMD_KEY]bugreport (report)
    
    Leaves a bug report on the official BattleBanana server and trello.
    
    """

    await bug_reporter.send_report(ctx, report)


@commands.command(permission=Permission.DISCORD_USER, args_pattern="S")
@commands.ratelimit(cooldown=300, error=":hushed: Please no more suggestions (for a few minutes)!")
async def suggest(ctx, suggestion, **_):
    """
    [CMD_KEY]suggest (suggestion)
    
    Leaves a suggestion on the official BattleBanana server and trello.
    
    """

    await suggestion_sender.send_report(ctx, suggestion)
