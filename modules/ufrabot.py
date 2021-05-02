"""Ultimate module for the UFRA TS."""
from ts3API.TS3Connection import TS3QueryException
import ts3API.Events as Events

import Bot
import Moduleloader
from Moduleloader import *
#import random
#import codecs

from modules.ufrasettings import *

bot: None
# Server groups who should not receiver quotes upon joining the server
dont_send = []


ufrabot_channel_event_handler = None

@Moduleloader.setup
def setup_ufrabot(ts3bot):
    """
    Setup the quoter. Define groups not to send quotes to.
    :return:
    """
  
    #global bot, dont_send
    groups = [group_henker, group_officier]

    global bot
    bot = ts3bot
    ts3conn = bot.ts3conn

# @Moduleloader.channel_event(Events.ClientMovedSelfEvent, 1047, 1045,)
# def on_channel_join_event(evt):
#     """
#     Create a temporary channel 
#     """
#     response = bot.ts3conn._send("channelcreate", ["channel_name=My\sChannel","channel_topic=My\sTopic"])    
#     cid = response.decode(encoding='UTF-8').split("=", 1)[1]
#     response = bot.ts3conn._send("channelmove", ["cid="+ cid, "cpid="+str(evt.target_channel_id)])
#     bot.ts3conn.clientmove(int(cid), evt.client_id)
#     _bot_go_home()

# def on_channel_message_event(_sender, **kw):
#     pass

# def _bot_go_home():
#     bot.ts3conn.clientmove(bot.default_channel, int(bot.ts3conn.whoami()["client_id"]))


@Moduleloader.event(Events.ClientEnteredEvent,)
def inform(evt):
    """
    Send out a quote to joining users.
    :param evt: ClientEnteredEvent
    """
    for g in evt.client_servergroups.split(','):
        if len(g) == 0 or int(g) in dont_send:
            return

    #Bot.send_msg_to_client(bot.ts3conn, evt.client_id, "foobar")


def on_channel_event(self, _sender, **kw):
    if type(parsed_event) is Events.ClientMovedEvent:
        logging.debug(type(parsed_event))
        Bot.send_msg_to_client(bot.ts3conn, evt.client_id, "hello")
    else:
        logging.debug(type(parsed_event))


@command('foobar', )
@group('Henker', )
def foobar(sender, msg):
    """
    send foobar.
    """
    Bot.send_msg_to_client(bot.ts3conn, sender, "foobar")


# @Moduleloader.event(Events.ClientEnteredEvent,)
# def applicant_join(event):
#     """
#     If a client joined the Bewerbungschannel
#     """


#     # for g in ts3conn.servergrouplist():
#     #         if g.get('name', '') in ["Guest", "Admin Server Query"]:
#     #             dont_send.append(int(g.get('sgid', 0)))

#     clinfo = Bot.ts3conn.clientinfo()

#     target_chan = event._target_channel_id
#     client_id = event.client_id

#     #clientinfo

#     # if (event.target_channel_id == channel_applicants_id) and 
#     #     (event.client_id  )

# def _get_online_recruiter():
#     """
#     Returns a list of user id wich are reqcruiter    
#     """
#     recruiter = []

#     # for role in group_recruitofficer:
#     #     s

#     # clinfo = Bot.ts3conn.

#     target_chan = event._target_channel_id
#     client_id = event.client_id

# def _get_online_perso():
#     """
#     Returns a list of user id wich are personal officers
#     """
#     pass
