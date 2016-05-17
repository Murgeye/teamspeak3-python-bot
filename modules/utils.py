from Moduleloader import *
import Bot
import logging
__version__="0.2"
bot = None
logger = logging.getLogger("bot")

@setup
def setup(ts3Bot):
    global bot
    bot = ts3Bot

@command('hello',)
def hello(sender, msg):
    Bot.send_msg_to_client(bot.ts3conn, sender, "Hello World")

@command('kickme','fuckme')
def kickme(sender, msg):
    ts3conn = bot.ts3conn
    ts3conn.clientkick(sender,5,"Wie du willst.")

@command('multimove',)
def multi_move(sender, msg):
    channels = msg[len("!multimove "):].split()
    source_name = ""
    dest_name = ""
    source = None
    dest = None
    ts3conn = bot.ts3conn
    if len(channels) < 2:
        if sender != 0:
            Bot.send_msg_to_client(ts3conn, sender, "Usage: multimove source destination")
            return
    elif len(channels) > 2:
        channel_name_list = ts3conn.channel_name_list()
        for channel_name in channel_name_list:
            if msg[len("!multimove "):].startswith(channel_name):
                source_name = channel_name
                dest_name = msg[len("!multimove ") + len(source_name)+1:]
    else:
        source_name = channels[0]
        dest_name = channels[1]
    if source_name == "":
        Bot.send_msg_to_client(ts3conn, sender, "Source channel not found")
        return
    if dest_name == "":
        Bot.send_msg_to_client(ts3conn, sender, "Destination channel not found")
        return
    try:
        channel_candidates = ts3conn.channelfind_by_name(source_name)
        if len(channel_candidates) > 0:
            source = channel_candidates[0].get("cid", '-1')
        if source is None or source == "-1":
            Bot.send_msg_to_client(ts3conn, sender, "Source channel not found")
            return
    except TS3QueryException:
        Bot.send_msg_to_client(ts3conn, sender, "Source channel not found")
    try:
        channel_candidates = ts3conn.channelfind_by_name(dest_name)
        if len(channel_candidates) > 0:
            dest = channel_candidates[0].get("cid", '-1')
        if dest is None or dest == "-1":
            Bot.send_msg_to_client(ts3conn, sender, "Destination channel not found")
            return
    except TS3QueryException:
        Bot.send_msg_to_client(ts3conn, sender, "Destination channel not found")
    try:
        clientlist = ts3conn.clientlist()
        #logger.info(str(clientlist))
        #logger.info("Moving all from " + source + " to " + dest)
        clientlist = [client for client in clientlist if client.get("cid", '-1') == source]
        for client in clientlist:
            clid = client.get("clid", '-1')
            logger.info("Found client in channel: " + client.get("client_nickname", "") + " id = " + clid)
            ts3conn.clientmove(int(dest), int(clid))
    except TS3QueryException as e:
        Bot.send_msg_to_client(ts3conn, sender, "Error moving clients: id = " +
                str(e.id) + e.message)

@command('version',)
def send_version(sender, msg):
    Bot.send_msg_to_client(bot.ts3conn, sender, __version__)

@command('whoami',)
def whoami(sender, msg):
    Bot.send_msg_to_client(bot.ts3conn, sender, "None of your business!")
