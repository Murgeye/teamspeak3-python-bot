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


    #ufrabot_channel_event_handler = CommandHandler.CommandHandler(self.ts3conn)
    #self.event_handler = EventHandler.EventHandler(ts3conn=self.ts3conn, command_handler=self.command_handler)

    #def register_for_channel_events(self, channel_id, event_listener=None, weak_ref=True):    
    try:
        ts3conn.register_for_channel_events(1045, on_channel_event)
    except ts3API.TS3Connection.TS3QueryException:
        self.logger.exception("Error on registering for channel event.")
        exit()


    # for g in ts3conn.servergrouplist():
    #     if g.get('name', '') in ["Guest", "Admin Server Query"]:
    #         dont_send.append(int(g.get('sgid', 0)))


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


@Moduleloader.event(Events.ClientEnteredEvent,)
def applicant_join(event):
    """
    If a client joined the Bewerbungschannel
    """


    # for g in ts3conn.servergrouplist():
    #         if g.get('name', '') in ["Guest", "Admin Server Query"]:
    #             dont_send.append(int(g.get('sgid', 0)))

    clinfo = Bot.ts3conn.clientinfo()

    target_chan = event._target_channel_id
    client_id = event.client_id

    #clientinfo

    # if (event.target_channel_id == channel_applicants_id) and 
    #     (event.client_id  )

def _get_online_recruiter():
    """
    Returns a list of user id wich are reqcruiter    
    """
    recruiter = []

    # for role in group_recruitofficer:
    #     s

    # clinfo = Bot.ts3conn.

    target_chan = event._target_channel_id
    client_id = event.client_id

def _get_online_perso():
    """
    Returns a list of user id wich are personal officers
    """
    pass

# @event(Events.ClientLeftEvent,)
# def client_left(event):
#     """
#     Clean up leaving clients.
#     """
#     # Forgets clients that were set to afk and then left
#     if afkMover is not None:
#         if str(event.client_id) in afkMover.client_channels:
#             del afkMover.client_channels[str(event.client_id)]