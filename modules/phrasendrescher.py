# standard imports
import os
import sqlite3

# third-party imports
from ts3API.Events import ClientEnteredEvent

# local imports
import teamspeak_bot
from module_loader import setup_plugin, command, event

bot: teamspeak_bot.Ts3Bot
path: str
# Server groups who should not receive quotes upon joining the server
dont_send = []


@setup_plugin
def setup_quoter(ts3bot, database_filename):
    """
    Setup the quoter. Define groups not to send quotes to.
    :return:
    """
    global bot, dont_send, path
    bot = ts3bot
    ts3conn = bot.ts3conn

    for servergroup in ts3conn.servergrouplist():
        if servergroup.get('name', '') in ["Guest", "Admin Server Query"]:
            dont_send.append(int(servergroup.get('sgid', 0)))

    if not os.path.isabs(database_filename):
        path = os.path.dirname(__file__)
        path = os.path.join(path, database_filename)
    else:
        path = database_filename

    path = os.path.abspath(path)
    # setup and connect to database
    conn = sqlite3.connect(path)
    curs = conn.cursor()
    curs.execute('CREATE TABLE IF NOT EXISTS Quotes (id integer primary key, quote text,'
                 'submitter text, time text, shown integer)')
    curs.execute('CREATE UNIQUE INDEX IF NOT EXISTS Quotesididx ON Quotes (id)')
    conn.commit()
    conn.close()


@command('quote',)
def add_quote(sender, msg):
    """Adds a new quote to the database."""
    if len(msg) <= len('!quote '):
        teamspeak_bot.send_msg_to_client(bot.ts3conn, sender, 'Please include a quote to save.')
    else:
        conn = sqlite3.connect(path)
        curs = conn.cursor()
        quote = msg[len('!quote')+1:]
        quote = quote.replace('" ', '"\n')
        submitter = bot.ts3conn.clientinfo(sender)
        submitter = submitter['client_nickname']
        curs.execute('INSERT INTO Quotes (quote, submitter, time, shown) VALUES (?, ?,'
                  'strftime("%s", "now"), ?)', (quote, submitter, 0))
        conn.commit()
        conn.close()
        teamspeak_bot.send_msg_to_client(bot.ts3conn, sender, 'Your quote has been saved!')


@event(ClientEnteredEvent)
def send_quote(evt):
    """Sends a random quote to a client."""
    for servergroup in evt.client_servergroups.split(','):
        if len(servergroup) == 0 or int(servergroup) in dont_send:
            return

    conn = sqlite3.connect(path)
    curs = conn.cursor()
    curs.execute('SELECT * FROM Quotes ORDER BY RANDOM() LIMIT 1')
    quote = curs.fetchone()
    teamspeak_bot.send_msg_to_client(bot.ts3conn, evt.client_id, quote[1])
    curs.execute('UPDATE Quotes SET shown=? WHERE id=?', (quote[4] + 1, quote[0]))
    conn.commit()
    conn.close()
