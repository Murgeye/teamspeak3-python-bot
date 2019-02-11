"""Quote module for the Teamspeak 3 Bot. Sends quotes to people joining the server."""
import Bot
import Moduleloader
import ts3.Events as Events
import sqlite3
import sys
import os

bot = None
path = None
# Server groups who should not receiver quotes upon joining the server
dont_send = []


@Moduleloader.setup
def setup_quoter(ts3bot, db):
    """
    Setup the quoter. Define groups not to send quotes to.
    :return:
    """
    global bot, dont_send, path
    bot = ts3bot
    ts3conn = bot.ts3conn
    for g in ts3conn.servergrouplist():
        if g.get('name', '') in ["Guest", "Admin Server Query"]:
            dont_send.append(int(g.get('sgid', 0)))
    if not os.path.isabs(db):
        path = os.path.dirname(__file__)
        path = os.path.join(path, db)
    else:
        path = db
    path = os.path.abspath(path)
    # setup and connect to database
    conn = sqlite3.connect(path)
    curs = conn.cursor()
    curs.execute('CREATE TABLE IF NOT EXISTS Quotes (id integer primary key, quote text, submitter text, time text, shown integer)')
    curs.execute('CREATE UNIQUE INDEX IF NOT EXISTS Quotesididx ON Quotes (id)')
    conn.commit()
    conn.close()


@Moduleloader.command('quote',)
def add_quote(sender, msg):
    if len(msg) <= len('!quote '):
        Bot.send_msg_to_client(bot.ts3conn, sender, 'Please include a quote to save.')
    else:
        conn = sqlite3.connect(path)
        c = conn.cursor()
        quote = msg[len('!quote')+1:]
        quote = quote.replace('" ', '"\n')
        submitter = bot.ts3conn.clientinfo(sender)
        submitter = submitter['client_nickname']
        c.execute('INSERT INTO Quotes (quote, submitter, time, shown) VALUES (?, ?, strftime("%s", "now"), ?)', (quote, submitter, 0))
        conn.commit()
        conn.close()
        Bot.send_msg_to_client(bot.ts3conn, sender, 'Your quote has been saved!')


@Moduleloader.event(Events.ClientEnteredEvent,)
def send_quote(evt):
    for g in evt.client_servergroups.split(','):
        if len(g) == 0 or int(g) in dont_send:
            return
    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.execute('SELECT * FROM Quotes ORDER BY RANDOM() LIMIT 1')
    quote = c.fetchone()
    Bot.send_msg_to_client(bot.ts3conn, evt.client_id, quote[1])
    c.execute('UPDATE Quotes SET shown=? WHERE id=?', (quote[4] + 1, quote[0]))
    conn.commit()
    conn.close()

