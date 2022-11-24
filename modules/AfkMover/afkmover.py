"""AfkMover Module for the Teamspeak3 Bot."""
import threading
import traceback
from threading import Thread

import ts3API.Events as Events
from ts3API.utilities import TS3Exception

from Moduleloader import *
import Bot
from typing import Union

afkMover: Union[None, 'AfkMover'] = None
afkStopper = threading.Event()
bot: Bot.Ts3Bot
autoStart = True
channel_name = "AFK"


class AfkMover(Thread):
    """
    AfkMover class. Moves clients set to afk another channel.
    """
    logger = logging.getLogger("afk")
    logger.propagate = 0
    logger.setLevel(logging.WARNING)
    file_handler = logging.FileHandler("afk.log", mode='a+')
    formatter = logging.Formatter('AFK Logger %(asctime)s %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.info("Configured afk logger")
    logger.propagate = 0

    def __init__(self, stop_event, ts3conn):
        """
        Create a new AfkMover object.
        :param stop_event: Event to signalize the AfkMover to stop moving.
        :type stop_event: threading.Event
        :param ts3conn: Connection to use
        :type: TS3Connection
        """
        Thread.__init__(self)
        self.stopped = stop_event
        self.ts3conn = ts3conn
        self.afk_channel = self.get_afk_channel(channel_name)
        self.client_channels = {}
        self.afk_list = None
        if self.afk_channel is None:
            AfkMover.logger.error("Could not get afk channel")

    def run(self):
        """
        Thread run method. Starts the mover.
        """
        AfkMover.logger.info("AFKMove Thread started")
        try:
            self.auto_move_all()
        except BaseException:
            self.logger.exception("Exception occured in run:")

    def update_afk_list(self):
        """
        Update the list of clients.
        """
        try:
            self.afk_list = self.ts3conn.clientlist(["away"])
            AfkMover.logger.debug("Awaylist: " + str(self.afk_list))
        except TS3Exception:
            AfkMover.logger.exception("Error getting away list!")
            self.afk_list = list()

    def get_away_list(self):
        """
        Get list of clients with afk status.
        :return: List of clients that are set to afk.
        """
        if self.afk_list is not None:
            AfkMover.logger.debug(str(self.afk_list))
            awaylist = list()
            for client in self.afk_list:
                AfkMover.logger.debug(str(self.afk_list))
                if "cid" not in client.keys():
                    AfkMover.logger.error("Client without cid!")
                    AfkMover.logger.error(str(client))
                elif "client_away" in client.keys() and client.get("client_away", '0') == '1' \
                        and int(client.get("cid", '-1')) != int(self.afk_channel):
                    awaylist.append(client)
            return awaylist
        else:
            AfkMover.logger.error("Clientlist is None!")
            return list()

    def get_back_list(self):
        """
        Get list of clients in the afk channel, but not away.
        :return: List of clients who are back from afk.
        """
        clientlist = [client for client in self.afk_list if client.get("client_away", '1') == '0'
                      and int(client.get("cid", '-1')) == int(self.afk_channel)]
        return clientlist

    def get_afk_channel(self, name="AFK"):
        """
        Get the channel id of the channel specified by name.
        :param name: Channel name
        :return: Channel id
        """
        try:
            channel = self.ts3conn.channelfind(name)[0].get("cid", '-1')
        except TS3Exception:
            AfkMover.logger.exception("Error getting afk channel")
            raise
        return channel

    def move_to_afk(self, clients):
        """
        Move clients to the afk_channel.
        :param clients: List of clients to move.
        """
        AfkMover.logger.info("Moving clients to afk!")
        for client in clients:
            AfkMover.logger.info("Moving somebody to afk!")
            AfkMover.logger.debug("Client: " + str(client))
            try:
                self.ts3conn.clientmove(self.afk_channel, int(client.get("clid", '-1')))
            except TS3Exception:
                AfkMover.logger.exception("Error moving client! Clid=" +
                                          str(client.get("clid", '-1')))
            self.client_channels[client.get("clid", '-1')] = client.get("cid", '0')
            AfkMover.logger.debug("Moved List after move: " + str(self.client_channels))

    def move_all_afk(self):
        """
        Move all afk clients.
        """
        try:
            afk_list = self.get_away_list()
            self.move_to_afk(afk_list)
        except AttributeError:
            AfkMover.logger.exception("Connection error!")

    def move_all_back(self):
        """
        Move all clients who are back from afk.
        """
        back_list = self.get_back_list()
        AfkMover.logger.debug("Moving clients back")
        AfkMover.logger.debug("Backlist is: %s", str(back_list))
        AfkMover.logger.debug("Saved channel list keys are: %s\n", str(self.client_channels.keys()))
        for client in back_list:
            if client.get("clid", -1) in self.client_channels.keys():
                AfkMover.logger.info("Moving a client back!")
                AfkMover.logger.debug("Client: " + str(client))
                AfkMover.logger.debug("Saved channel list keys:" + str(self.client_channels))
                self.ts3conn.clientmove(self.client_channels.get(client.get("clid", -1)),
                                        int(client.get("clid", '-1')))
                del self.client_channels[client.get("clid", '-1')]

    def auto_move_all(self):
        """
        Loop move functions until the stop signal is sent.
        """
        while not self.stopped.wait(2.0):
            AfkMover.logger.debug("Afkmover running!")
            self.update_afk_list()
            try:
                self.move_all_back()
                self.move_all_afk()
            except BaseException:
                AfkMover.logger.error("Uncaught exception:" + str(sys.exc_info()[0]))
                AfkMover.logger.error(str(sys.exc_info()[1]))
                AfkMover.logger.error(traceback.format_exc())
                AfkMover.logger.error("Saved channel list keys are: %s\n",
                                      str(self.client_channels.keys()))
        AfkMover.logger.warning("AFKMover stopped!")
        self.client_channels = {}


@command('startafk', 'afkstart', 'afkmove',)
def start_afkmover(_sender=None, _msg=None):
    """
    Start the AfkMover by clearing the afkStopper signal and starting the mover.
    """
    global afkMover
    if afkMover is None:
        afkMover = AfkMover(afkStopper, bot.ts3conn)
        afkStopper.clear()
        afkMover.start()


@command('stopafk', 'afkstop')
def stop_afkmover(_sender=None, _msg=None):
    """
    Stop the AfkMover by setting the afkStopper signal and undefining the mover.
    """
    global afkMover
    afkStopper.set()
    afkMover = None


@command('afkgetclientchannellist')
def get_afk_list(sender=None, _msg=None):
    """
    Get afkmover saved client channels. Mainly for debugging.
    """
    if afkMover is not None:
        Bot.send_msg_to_client(bot.ts3conn, sender, str(afkMover.client_channels))


@event(Events.ClientLeftEvent,)
def client_left(event_data):
    """
    Clean up leaving clients.
    """
    # Forget clients that were set to afk and then left
    if afkMover is not None:
        if str(event_data.client_id) in afkMover.client_channels:
            del afkMover.client_channels[str(event_data.client_id)]


@setup
def setup(ts3bot, channel=channel_name):
    global bot, channel_name
    bot = ts3bot
    channel_name = channel
    if autoStart:
        start_afkmover()


@exit
def afkmover_exit():
    global afkMover
    if afkMover is not None:
        afkStopper.set()
        afkMover.join()
        afkMover = None


