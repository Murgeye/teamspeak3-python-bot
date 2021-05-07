from ts3API.TS3Connection import TS3QueryException

import Bot
import Moduleloader
from Moduleloader import *

__version__ = "0.4"
bot = None
logger = logging.getLogger("bot")


@Moduleloader.setup
def setup(ts3bot):
    global bot
    bot = ts3bot


@command('hello', )
@group('Admin', )
def hello(sender, _msg):
    Bot.send_msg_to_client(bot.ts3conn, sender, "Hello Admin!")


@command('hello', )
@group('Moderator', )
def hello(sender, _msg):
    Bot.send_msg_to_client(bot.ts3conn, sender, "Hello Moderator!")


@command('hello', )
@group('Normal', )
def hello(sender, _msg):
    Bot.send_msg_to_client(bot.ts3conn, sender, "Hello Casual!")


@command('kickme', 'fuckme')
@group('.*', )
def kickme(sender, _msg):
    ts3conn = bot.ts3conn
    ts3conn.clientkick(sender, 5, "Whatever.")


@command('mtest', )
def mtest(_sender, msg):
    print("MTES")
    channels = msg[len("!mtest "):].split()
    print(channels)
    ts3conn = bot.ts3conn
    print(ts3conn.channelfind(channels[0]))


@command('multimove', 'mm')
@group('Server Admin', 'Moderator')
def multi_move(sender, msg):
    """
    Move all clients from one channel to another.
    :param sender: Client id of sender that sent the command.
    :param msg: Sent command.
    """
    channels = msg.split()[1:]
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
                dest_name = msg[len("!multimove ") + len(source_name) + 1:]
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
        channel_matches = ts3conn.channelfind(source_name)
        channel_candidates = [chan for chan in channel_matches if
                              chan.get("channel_name", '-1').startswith(source_name)]
        if len(channel_candidates) == 1:
            source = channel_candidates[0].get("cid", '-1')
        elif len(channel_candidates) == 0:
            Bot.send_msg_to_client(ts3conn, sender, "Source channel could not be found.")
        else:
            channels = [chan.get('channel_name') for chan in channel_candidates]
            Bot.send_msg_to_client(ts3conn, sender,
                                   "Multiple source channels found: " + ", ".join(channels))
    except TS3QueryException:
        Bot.send_msg_to_client(ts3conn, sender, "Source channel not found")
    try:
        channel_matches = ts3conn.channelfind(dest_name)
        channel_candidates = [chan for chan in channel_matches if
                              chan.get("channel_name", '-1').startswith(dest_name)]
        if len(channel_candidates) == 1:
            dest = channel_candidates[0].get("cid", '-1')
        elif len(channel_candidates) == 0:
            Bot.send_msg_to_client(ts3conn, sender, "Destination channel could not be found.")
        else:
            channels = [chan.get('channel_name') for chan in channel_candidates]
            Bot.send_msg_to_client(ts3conn, sender,
                                   "Multiple destination channels found: " + ", ".join(channels))
    except TS3QueryException:
        Bot.send_msg_to_client(ts3conn, sender, "Destination channel not found")
    if source is not None and dest is not None:
        try:
            client_list = ts3conn.clientlist()
            client_list = [client for client in client_list if client.get("cid", '-1') == source]
            for client in client_list:
                clid = client.get("clid", '-1')
                logger.info("Found client in channel: " + client.get("client_nickname",
                                                                     "") + " id = " + clid)
                ts3conn.clientmove(int(dest), int(clid))
        except TS3QueryException as e:
            Bot.send_msg_to_client(ts3conn, sender,
                                   "Error moving clients: id = " + str(e.id) + e.message)


@command('version', )
@group('.*')
def send_version(sender, _msg):
    Bot.send_msg_to_client(bot.ts3conn, sender, __version__)


@command('whoami', )
@group('.*')
def whoami(sender, _msg):
    Bot.send_msg_to_client(bot.ts3conn, sender, "None of your business!")


@command('stop', )
@group('Server Admin', )
def stop_bot(_sender, _msg):
    Moduleloader.exit_all()
    bot.ts3conn.quit()
    logger.warning("Bot was quit!")


@command('restart', )
@group('Server Admin', 'Moderator', )
def restart_bot(_sender, _msg):
    Moduleloader.exit_all()
    bot.ts3conn.quit()
    logger.warning("Bot was quit!")
    import main
    main.restart_program()


@command('commandlist', )
@group('Server Admin', 'Moderator', )
def get_command_list(sender, _msg):
    Bot.send_msg_to_client(bot.ts3conn, sender, str(list(bot.command_handler.handlers.keys())))
