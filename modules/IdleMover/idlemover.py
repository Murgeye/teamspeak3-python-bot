"""IdleMover Module for the Teamspeak3 Bot."""
import threading
import traceback
from threading import Thread

import ts3API.Events as Events
from ts3API.utilities import TS3Exception

from Moduleloader import *
import Bot
from typing import Union

idleMover: Union[None, 'IdleMover'] = None
idleStopper = threading.Event()
bot: Bot.Ts3Bot
autoStart = True
channel_name = "Idle"
min_idle_time_seconds = 5 * 60 # 5 minutes


class IdleMover(Thread):
    """
    IdleMover class. Moves clients with idle state to idle channel.
    """
    logger = logging.getLogger("IdleMover")
    logger.propagate = 0
    logger.setLevel(logging.WARNING)
    file_handler = logging.FileHandler("idlemover.log", mode='a+')
    formatter = logging.Formatter('IdleMover Logger %(asctime)s %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.info("Configured IdleMover logger")
    logger.propagate = 0

    def __init__(self, stop_event, ts3conn):
        """
        Create a new IdleMover object.
        :param stop_event: Event to signalize the IdleMover to stop moving.
        :type stop_event: threading.Event
        :param ts3conn: Connection to use
        :type: TS3Connection
        """
        Thread.__init__(self)
        self.stopped = stop_event
        self.ts3conn = ts3conn
        self.idle_channel = self.get_idle_channel(channel_name)
        self.client_channels = {}
        self.idle_list = None
        if self.idle_channel is None:
            IdleMover.logger.error("Could not get idle channel")

    def run(self):
        """
        Thread run method. Starts the mover.
        """
        IdleMover.logger.info("IdleMove Thread started")
        try:
            self.auto_move_all()
        except BaseException:
            self.logger.exception("Exception occured in run:")

    def update_idle_list(self):
        """
        Update the list of idle clients.
        """
        try:
            self.idle_list = self.ts3conn.clientlist(["away"])
            IdleMover.logger.debug("Idle list: " + str(self.idle_list))
        except TS3Exception:
            IdleMover.logger.exception("Error getting idle list!")
            self.idle_list = list()

    def get_idle_list(self):
        """
        Get list of idle clients.
        :return: List of clients that are idle since a specific amount of time.
        """
        if self.idle_list is not None:
            IdleMover.logger.debug(str(self.idle_list))
            idle_list = list()
            for client in self.idle_list:
                IdleMover.logger.debug(str(self.idle_list))
                if "cid" not in client.keys():
                    IdleMover.logger.error("Client without cid!")
                    IdleMover.logger.error(str(client))
                elif "client_idle_time" in client.keys() and client.get("client_idle_time", '0') >= min_idle_time_seconds \
                        and int(client.get("cid", '-1')) != int(self.idle_channel):
                    idle_list.append(client)
            return idle_list
        else:
            IdleMover.logger.error("Clientlist is None!")
            return list()

    def get_back_list(self):
        """
        Get list of clients in the idle channel, but not idle anymore.
        :return: List of clients who are not idle anymore.
        """
        client_list = [client for client in self.idle_list if client.get("client_idle_time", '1') <= min_idle_time_seconds
                      and int(client.get("cid", '-1')) == int(self.idle_channel)]
        return client_list

    def get_idle_channel(self, name="Idle"):
        """
        Get the channel id of the channel specified by name.
        :param name: Channel name
        :return: Channel id
        """
        try:
            channel = self.ts3conn.channelfind(name)[0].get("cid", '-1')
        except TS3Exception:
            IdleMover.logger.exception("Error getting idle channel")
            raise
        return channel

    def move_to_idle(self, clients):
        """
        Move clients to the idle_channel.
        :param clients: List of clients to move.
        """
        IdleMover.logger.info("Moving clients to idle!")
        for client in clients:
            IdleMover.logger.info("Moving somebody to idle!")
            IdleMover.logger.debug("Client: " + str(client))
            try:
                self.ts3conn.clientmove(self.idle_channel, int(client.get("clid", '-1')))
            except TS3Exception:
                IdleMover.logger.exception("Error moving client! Clid=" +
                                          str(client.get("clid", '-1')))
            self.client_channels[client.get("clid", '-1')] = client.get("cid", '0')
            IdleMover.logger.debug("Moved list after move: " + str(self.client_channels))

    def move_all_idle(self):
        """
        Move all idle clients.
        """
        try:
            idle_list = self.get_idle_list()
            self.move_to_idle(idle_list)
        except AttributeError:
            IdleMover.logger.exception("Connection error!")

    def move_all_back(self):
        """
        Move all clients back who are not idle anymore.
        """
        back_list = self.get_back_list()
        IdleMover.logger.debug("Moving clients back")
        IdleMover.logger.debug("Backlist is: %s", str(back_list))
        IdleMover.logger.debug("Saved channel list keys are: %s\n", str(self.client_channels.keys()))
        for client in back_list:
            if client.get("clid", -1) in self.client_channels.keys():
                IdleMover.logger.info("Moving a client back!")
                IdleMover.logger.debug("Client: " + str(client))
                IdleMover.logger.debug("Saved channel list keys:" + str(self.client_channels))
                self.ts3conn.clientmove(self.client_channels.get(client.get("clid", -1)),
                                        int(client.get("clid", '-1')))
                del self.client_channels[client.get("clid", '-1')]

    def auto_move_all(self):
        """
        Loop move functions until the stop signal is sent.
        """
        while not self.stopped.wait(2.0):
            IdleMover.logger.debug("IdleMover running!")
            self.update_idle_list()
            try:
                self.move_all_back()
                self.move_all_idle()
            except BaseException:
                IdleMover.logger.error("Uncaught exception:" + str(sys.exc_info()[0]))
                IdleMover.logger.error(str(sys.exc_info()[1]))
                IdleMover.logger.error(traceback.format_exc())
                IdleMover.logger.error("Saved channel list keys are: %s\n",
                                      str(self.client_channels.keys()))
        IdleMover.logger.warning("IdleMover stopped!")
        self.client_channels = {}


@command('startidle', 'idlestart', 'idlemove',)
def start_idlemover(_sender=None, _msg=None):
    """
    Start the IdleMover by clearing the idleStopper signal and starting the mover.
    """
    global idleMover
    if idleMover is None:
        idleMover = IdleMover(idleStopper, bot.ts3conn)
        idleStopper.clear()
        idleMover.start()


@command('stopidle', 'idlestop')
def stop_idlemover(_sender=None, _msg=None):
    """
    Stop the IdleMover by setting the idleStopper signal and undefining the mover.
    """
    global idleMover
    idleStopper.set()
    idleMover = None


@command('idlegetclientchannellist')
def get_idle_list(sender=None, _msg=None):
    """
    Get IdleMover saved client channels. Mainly for debugging.
    """
    if idleMover is not None:
        Bot.send_msg_to_client(bot.ts3conn, sender, str(idleMover.client_channels))


@event(Events.ClientLeftEvent,)
def client_left(event_data):
    """
    Clean up left clients.
    """
    # Forget clients that were idle and then left
    if idleMover is not None:
        if str(event_data.client_id) in idleMover.client_channels:
            del idleMover.client_channels[str(event_data.client_id)]


@setup
def setup(ts3bot, channel=channel_name):
    global bot, channel_name
    bot = ts3bot
    channel_name = channel
    if autoStart:
        start_idlemover()


@exit
def idlemover_exit():
    global idleMover
    if idleMover is not None:
        idleStopper.set()
        idleMover.join()
        idleMover = None
