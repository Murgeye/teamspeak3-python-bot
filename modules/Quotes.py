"""Quote module for the Teamspeak 3 Bot. Sends quotes to people joining the server."""
import codecs
import random

import ts3API.Events as Events

import Bot
import Moduleloader

bot: Bot.Ts3Bot
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


def add(q):
    """
    Add a new quote.
    :param q: Quote to add.
    """
    with codecs.open("quotes", "a+", "ISO-8859-1") as f:
        f.write(q+"\n")


@Moduleloader.setup
def setup_quoter(ts3bot):
    """
    Setup the quoter. Define groups not to send quotes to.
    :return:
    """
    global bot, dont_send
    bot = ts3bot
    ts3conn = bot.ts3conn
    for g in ts3conn.servergrouplist():
        if g.get('name', '') in ["Guest", "Admin Server Query"]:
            dont_send.append(int(g.get('sgid', 0)))


@Moduleloader.event(Events.ClientEnteredEvent,)
def inform(evt):
    """
    Send out a quote to joining users.
    :param evt: ClientEnteredEvent
    """
    for g in evt.client_servergroups.split(','):
        if len(g) == 0 or int(g) in dont_send:
            return
    with codecs.open("quotes", "r", "ISO-8859-1") as f:
        quote = ""
        while len(quote) == 0:
            quote = random_line(f)
        Bot.send_msg_to_client(bot.ts3conn, evt.client_id, quote)


@Moduleloader.command('addquote',)
def add_quote(sender, msg):
    """
    Add a quote.
    """
    if len(msg) > len("!addQuote "):
        add(msg[len("!addQuote "):])
        Bot.send_msg_to_client(bot.ts3conn, sender, "Quote '" + msg[len("!addQuote "):] +
                               "' was added.")

