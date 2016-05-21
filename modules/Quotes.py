__author__ = 'Daniel'
import Bot
import sys
import random
import codecs
import Moduleloader
import ts3.Events as Events

bot = None
dont_send = []

def random_line(afile):
    line = next(afile)
    for num, aline in enumerate(afile):
        if random.randrange(num + 2):
            continue
        line = aline
    return line


def add(q):
    with codecs.open("quotes", "a+", "ISO-8859-1") as f:
        f.write(q+"\n")

@Moduleloader.setup
def setupQuoter(ts3Bot):
    global bot, dont_send
    bot = ts3Bot
    ts3conn =bot.ts3conn
    for g in ts3conn.servergrouplist():
        if g.get('name', '') in ["Guest", "Admin Server Query"]:
            dont_send.append(int(g.get('sgid', 0)))

@Moduleloader.event(Events.ClientEnteredEvent,)
def inform(evt):
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
    if len(msg) > len("!addQuote "):
        add(msg[len("!addQuote "):])
        Bot.send_msg_to_client(bot.ts3conn, sender, "Quote '" + msg[len("!addQuote "):] + "' was added.")

