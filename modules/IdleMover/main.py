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
plugin_stopper = threading.Event()
bot: Bot.Ts3Bot

# defaults for configureable options
autoStart = True
dry_run = False # log instead of performing actual actions
check_frequency = 30.0
enable_auto_move_back = True
idle_time_seconds = 600.0
channel_name = "AFK"

class IdleMover(Thread):
    """
    IdleMover class. Moves clients which are idle since more than `idle_time_seconds` seconds to the channel `channel_name`.
    """
    # configure logger
    class_name = __qualname__
    logger = logging.getLogger(class_name)
    logger.propagate = 0
    logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler(f"logs/{class_name.lower()}.log", mode='a+')
    formatter = logging.Formatter("%(asctime)s: %(levelname)s: %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.info(f"Configured {class_name} logger")
    logger.propagate = 0

    def __init__(self, stop_event, ts3conn):
        """
        Create a new IdleMover object.
        :param stop_event: Event to signalize the IdleMover to stop.
        :type stop_event: threading.Event
        :param ts3conn: Connection to use
        :type: TS3Connection
        """
        Thread.__init__(self)
        self.stopped = stop_event
        self.ts3conn = ts3conn
        self.afk_channel = self.get_afk_channel(channel_name)
        self.client_channels = {}
        self.idle_list = None
        if self.afk_channel is None:
            IdleMover.logger.error("Could not get afk channel")

    def run(self):
        """
        Thread run method. Starts the mover.
        """
        IdleMover.logger.info("AFKMove Thread started")
        try:
            self.auto_move_all()
        except BaseException:
            self.logger.exception("Exception occured in run:")

    def update_client_list(self):
        """
        Update list of clients with idle time.
        :return: List of connected clients with their idle time.
        """
        try:
            self.idle_list = []
            for client in self.ts3conn.clientlist(["times"]):
                if int(client.get("client_type")) == 1:
                    IdleMover.logger.debug(f"update_client_list ignoring ServerQuery client: {str(client)}")
                    continue

                self.idle_list.append(client)

            IdleMover.logger.debug(f"update_idle_list: {str(self.idle_list)}")
        except TS3Exception:
            IdleMover.logger.exception("Error getting away list!")
            self.idle_list = list()


    def get_idle_list(self):
        """
        Get list of clients which are idle since more than `idle_time_seconds` seconds.
        :return: List of clients which are idle.
        """
        if self.idle_list is not None:
            IdleMover.logger.debug(f"get_idle_list current awaylist: {str(self.idle_list)}!")
            client_idle_list = list()
            for client in self.idle_list:
                IdleMover.logger.debug(f"get_idle_list checking client: {str(client)}")

                if "cid" not in client.keys():
                    IdleMover.logger.error(f"get_idle_list client without cid: {str(client)}!")
                    continue

                if "client_idle_time" not in client.keys():
                    IdleMover.logger.error(f"get_idle_list client without client_idle_time: {str(client)}!")
                    continue

                if int(client.get("cid", '-1')) == int(self.afk_channel):
                    IdleMover.logger.debug(f"get_idle_list client is already in the afk_channel: {str(client)}!")
                    continue

                if int(client.get("client_idle_time")) / 1000 <= float(idle_time_seconds):
                    IdleMover.logger.debug(f"get_idle_list client is less or equal then {idle_time_seconds} seconds idle: {str(client)}!")
                    continue

                IdleMover.logger.debug(f"get_idle_list adding client to list: {str(client)}!")
                client_idle_list.append(client)

            IdleMover.logger.debug(f"get_idle_list updated awaylist: {str(client_idle_list)}!")

            return client_idle_list
        else:
            IdleMover.logger.debug("get_idle_list idle_list is None!")
            return list()

    def get_back_list(self):
        """
        Get list of clients which are in the afk channel, but not idle anymore.
        :return: List of clients which are not idle anymore.
        """
        if self.idle_list is not None:
            client_back_list = []
            for client in self.idle_list:
                IdleMover.logger.debug(f"get_back_list checking client: {str(client)}")

                if "cid" not in client.keys():
                    IdleMover.logger.error(f"get_back_list client without cid: {str(client)}!")
                    continue

                if "client_idle_time" not in client.keys():
                    IdleMover.logger.error(f"get_back_list client without client_idle_time: {str(client)}!")
                    continue

                if int(client.get("cid", '-1')) != int(self.afk_channel):
                    IdleMover.logger.debug(f"get_back_list client is not in the afk_channel anymore: {str(client)}!")
                    continue

                if int(client.get("client_idle_time")) / 1000 > float(idle_time_seconds):
                    IdleMover.logger.debug(f"get_back_list client is greater then {idle_time_seconds} seconds idle: {str(client)}!")
                    continue

                IdleMover.logger.debug(f"get_back_list adding client to list: {str(client)}!")
                client_back_list.append(client)

            IdleMover.logger.debug(f"get_back_list updated client list: {str(client_back_list)}!")
            return client_back_list
        else:
            IdleMover.logger.debug("get_back_list idle_list is None!")
            return list()

    def get_afk_channel(self, name="AFK"):
        """
        Get the channel id of the channel specified by name.
        :param name: Channel name
        :return: Channel id
        """
        try:
            channel = self.ts3conn.channelfind(name)[0].get("cid", '-1')
        except TS3Exception:
            IdleMover.logger.exception("Error getting afk channel")
            raise
        return channel

    def move_to_afk(self):
        """
        Move clients to the `afk_channel`.
        """
        idle_list = self.get_idle_list()
        if idle_list is not None:
            IdleMover.logger.info("Moving clients to afk!")
            for client in idle_list:
                IdleMover.logger.info("Moving somebody to afk!")
                IdleMover.logger.debug("Client: " + str(client))

                try:
                    self.ts3conn.clientmove(self.afk_channel, int(client.get("clid", '-1')))
                except TS3Exception:
                    IdleMover.logger.exception(f"Error moving client! Clid={str(client.get('clid', '-1'))}")

                self.client_channels[client.get("clid", '-1')] = client.get("cid", '0')

                IdleMover.logger.debug(f"Moved List after move: {str(self.client_channels)}")
        else:
            IdleMover.logger.debug("move_to_afk idle list is empty. Nothing todo.")

    def move_all_afk(self):
        """
        Move all idle clients.
        """
        try:
            self.move_to_afk()
        except AttributeError:
            IdleMover.logger.exception("Connection error!")

    def move_all_back(self):
        """
        Move all clients who are not idle anymore.
        """
        back_list = self.get_back_list()
        if back_list is not None:
            IdleMover.logger.debug("Moving clients back")
            IdleMover.logger.debug("Backlist is: %s", str(back_list))
            IdleMover.logger.debug("Saved channel list keys are: %s\n", str(self.client_channels.keys()))

            for client in back_list:
                if client.get("clid", -1) in self.client_channels.keys():
                    IdleMover.logger.info("Moving a client back!")
                    IdleMover.logger.debug("Client: " + str(client))
                    IdleMover.logger.debug("Saved channel list keys:" + str(self.client_channels))

                    self.ts3conn.clientmove(self.client_channels.get(client.get("clid", -1)), int(client.get("clid", '-1')))

                    del self.client_channels[client.get("clid", '-1')]
        else:
            IdleMover.logger.debug("move_all_back back list is empty. Nothing todo.")

    def auto_move_all(self):
        """
        Loop move functions until the stop signal is sent.
        """
        while not self.stopped.wait(float(check_frequency)):
            IdleMover.logger.debug("Afkmover running!")

            try:
                self.update_client_list()

                if enable_auto_move_back:
                    self.move_all_back()

                self.move_all_afk()
            except BaseException:
                IdleMover.logger.error("Uncaught exception:" + str(sys.exc_info()[0]))
                IdleMover.logger.error(str(sys.exc_info()[1]))
                IdleMover.logger.error(traceback.format_exc())
                IdleMover.logger.error("Saved channel list keys are: %s\n", str(self.client_channels.keys()))

        IdleMover.logger.warning("AFKMover stopped!")
        self.client_channels = {}


@command('startidle', 'idlestart')
def start_afkmover(_sender=None, _msg=None):
    """
    Start the IdleMover by clearing the plugin_stopper signal and starting the mover.
    """
    global idleMover
    if idleMover is None:
        if dry_run:
            IdleMover.logger.info("Dry run is enabled - logging actions intead of actually performing them.")

        idleMover = IdleMover(plugin_stopper, bot.ts3conn)
        plugin_stopper.clear()
        idleMover.start()


@command('stopidle', 'idlestop')
def stop_afkmover(_sender=None, _msg=None):
    """
    Stop the IdleMover by setting the plugin_stopper signal and undefining the mover.
    """
    global idleMover
    plugin_stopper.set()
    idleMover = None


@command('idlegetclientchannellist')
def get_afk_list(sender=None, _msg=None):
    """
    Get IdleMover saved client channels. Mainly for debugging.
    """
    if idleMover is not None:
        Bot.send_msg_to_client(bot.ts3conn, sender, str(idleMover.client_channels))


@event(Events.ClientLeftEvent)
def client_left(event_data):
    """
    Clean up leaving clients.
    """
    # Forget clients that were moved to the afk channel and then left
    if idleMover is not None:
        if str(event_data.client_id) in idleMover.client_channels:
            del idleMover.client_channels[str(event_data.client_id)]


@setup
def setup(ts3bot, auto_start = autoStart, enable_dry_run = dry_run, frequency = check_frequency, auto_move_back = enable_auto_move_back, min_idle_time_seconds = idle_time_seconds, channel = channel_name):
    global bot, autoStart, dry_run, check_frequency, enable_auto_move_back, idle_time_seconds, channel_name

    bot = ts3bot
    autoStart = auto_start
    dry_run = enable_dry_run
    check_frequency = frequency
    enable_auto_move_back = auto_move_back
    idle_time_seconds = min_idle_time_seconds
    channel_name = channel

    if autoStart:
        start_afkmover()


@exit
def afkmover_exit():
    global idleMover

    if idleMover is not None:
        plugin_stopper.set()
        idleMover.join()
        idleMover = None
