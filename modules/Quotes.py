# standard imports
import codecs
import random

# third-party imports
from ts3API.Events import ClientEnteredEvent

# local imports
import teamspeak_bot
from module_loader import setup_plugin, event, command

bot: teamspeak_bot.Ts3Bot
# Server groups who should not receiver quotes upon joining the server
dont_send = []


def random_line(afile):
    """
    Get a random line from a file.
    :param afile: File to read from.
    :return: Random line
    """
    line = next(afile)
    for num, aline in enumerate(afile):
        if random.randrange(num + 2):
            continue
        line = aline
    return line


def add(quote):
    """
    Add a new quote.
    :param quote: Quote to add.
    """
    with codecs.open("quotes", "a+", "ISO-8859-1") as quotes_file:
        quotes_file.write(f"{quote}\n")


@setup_plugin
def setup_quoter(ts3bot):
    """
    Setup the quoter. Define groups not to send quotes to.
    :return:
    """
    global bot, dont_send
    bot = ts3bot
    ts3conn = bot.ts3conn
    for servergroup in ts3conn.servergrouplist():
        if servergroup.get('name', '') in ["Guest", "Admin Server Query"]:
            dont_send.append(int(servergroup.get('sgid', 0)))


@event(ClientEnteredEvent)
def inform(evt):
    """
    Send out a quote to joining users.
    :param evt: ClientEnteredEvent
    """
    for servergroup in evt.client_servergroups.split(','):
        if len(servergroup) == 0 or int(servergroup) in dont_send:
            return

    with codecs.open("quotes", "r", "ISO-8859-1") as quotes_file:
        quote = ""
        while len(quote) == 0:
            quote = random_line(quotes_file)
        teamspeak_bot.send_msg_to_client(bot.ts3conn, evt.client_id, quote)


@command('addquote')
def add_quote(sender, msg):
    """
    Add a quote.
    """
    if len(msg) > len("!addQuote "):
        add(msg[len("!addQuote "):])
        teamspeak_bot.send_msg_to_client(bot.ts3conn, sender, f"Quote `{msg[len('!addQuote'):]}` was added.")
