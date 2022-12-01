import threading
import traceback
from threading import Thread

import ts3API.Events as Events
from ts3API.utilities import TS3Exception

from Moduleloader import *
import Bot
from typing import Union

plugin_command_name = "kickinactiveclients"
idleMover: Union[None, 'KickInactiveClients'] = None
plugin_stopper = threading.Event()
bot: Bot.Ts3Bot

# defaults for configureable options
autoStart = True
dry_run = False # log instead of performing actual actions
check_frequency = 60.0 * 5 # 300 seconds => 5 minutes
idle_time_seconds = 60.0 * 60 * 2 # 7200 seconds => 120 minutes => 2 hours
clientsonline_kick_threshold = 108 # Earliest start kicking clients when e.g. 108 of 128 slots are in use
kick_reason_message = "Sorry for kicking, but we need slots!"

class KickInactiveClients(Thread):
    """
    KickInactiveClients class. Kicks clients from the server which are idle since more than `idle_time_seconds` seconds.
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
        Create a new KickInactiveClients object.
        :param stop_event: Event to signalize the KickInactiveClients to stop.
        :type stop_event: threading.Event
        :param ts3conn: Connection to use
        :type: TS3Connection
        """
        Thread.__init__(self)
        self.stopped = stop_event
        self.ts3conn = ts3conn
        self.client_channels = {}
        self.idle_list = None
        self.serverinfo = None

    def run(self):
        """
        Thread run method. Starts the plugin.
        """
        KickInactiveClients.logger.info("Thread started")
        try:
            self.loop_until_stopped()
        except BaseException:
            self.logger.exception("Exception occured in run:")

    def get_serverinfo(self):
        """
        Get current serverinfo of the selected virtual server.
        :return: List of server information.
        """
        try:
            self.serverinfo = self.ts3conn.serverinfo()
        except TS3Exception:
            KickInactiveClients.logger.exception("Error getting server information!")
            self.serverinfo = list()

    def update_client_list(self):
        """
        Update list of clients with idle time.
        :return: List of connected clients with their idle time.
        """
        try:
            self.idle_list = []
            for client in self.ts3conn.clientlist(["times"]):
                if int(client.get("client_type")) == 1:
                    KickInactiveClients.logger.debug(f"update_client_list ignoring ServerQuery client: {str(client)}")
                    continue

                self.idle_list.append(client)

            KickInactiveClients.logger.debug(f"update_idle_list: {str(self.idle_list)}")
        except TS3Exception:
            KickInactiveClients.logger.exception("Error getting client list!")
            self.idle_list = list()


    def get_idle_list(self):
        """
        Get list of clients which are idle since more than `idle_time_seconds` seconds.
        :return: List of clients which are idle.
        """
        if self.idle_list is None:
            KickInactiveClients.logger.debug("get_idle_list idle_list is None!")
            return list()

        KickInactiveClients.logger.debug(f"get_idle_list current idle_list: {str(self.idle_list)}!")

        client_idle_list = list()
        for client in self.idle_list:
            KickInactiveClients.logger.debug(f"get_idle_list checking client: {str(client)}")

            if "cid" not in client.keys():
                KickInactiveClients.logger.error(f"get_idle_list client without cid: {str(client)}!")
                continue

            if "client_idle_time" not in client.keys():
                KickInactiveClients.logger.error(f"get_idle_list client without client_idle_time: {str(client)}!")
                continue

            if int(client.get("client_idle_time")) / 1000 <= float(idle_time_seconds):
                KickInactiveClients.logger.debug(f"get_idle_list client is less or equal then {idle_time_seconds} seconds idle: {str(client)}!")
                continue

            KickInactiveClients.logger.debug(f"get_idle_list adding client to list: {str(client)}!")
            client_idle_list.append(client)

        KickInactiveClients.logger.debug(f"get_idle_list updated idle_list: {str(client_idle_list)}!")

        return client_idle_list

    def kick_all_idle_clients(self):
        """
        Kick all idle clients.
        """
        virtualserver_clientsonline = self.serverinfo.get("virtualserver_clientsonline")
        if int(virtualserver_clientsonline) < int(clientsonline_kick_threshold):
            KickInactiveClients.logger.debug(f"Only {virtualserver_clientsonline} of {int(self.serverinfo.get('virtualserver_maxclients'))} slots used. Nothing todo.")
            return

        idle_list = self.get_idle_list()
        if idle_list is None:
            KickInactiveClients.logger.debug("kick_all_idle_clients idle_list is empty. Nothing todo.")
            return

        KickInactiveClients.logger.info(f"Kicking {len(idle_list)} clients from the server!")

        for client in idle_list:
            KickInactiveClients.logger.debug(f"Kicking the following client from the server: {str(client)}")

            if dry_run:
                KickInactiveClients.logger.info(f"I would have kicked the following client from the server, when the dry-run would be disabled: {str(client)}")
            else:
                try:
                    self.ts3conn.clientkick(int(client.get("clid", '-1')), 5, kick_reason_message)
                except TS3Exception:
                    KickInactiveClients.logger.exception(f"Error kicking client clid={str(client.get('clid', '-1'))}!")

    def loop_until_stopped(self):
        """
        Loop move functions until the stop signal is sent.
        """
        while not self.stopped.wait(float(check_frequency)):
            KickInactiveClients.logger.debug("Thread running!")

            try:
                self.get_serverinfo()
                self.update_client_list()
                self.kick_all_idle_clients()
            except BaseException:
                KickInactiveClients.logger.error("Uncaught exception:" + str(sys.exc_info()[0]))
                KickInactiveClients.logger.error(str(sys.exc_info()[1]))
                KickInactiveClients.logger.error(traceback.format_exc())

        KickInactiveClients.logger.warning("Thread stopped!")
        self.client_channels = {}


@command(f"{plugin_command_name} start")
def start_plugin(_sender=None, _msg=None):
    """
    Start the KickInactiveClients by clearing the plugin_stopper signal and starting the plugin.
    """
    global idleMover
    if idleMover is None:
        if len(kick_reason_message) > 40:
            KickInactiveClients.logger.error(f"The `kick_message` has {len(kick_reason_message)} characters, but only 40 are supported! Aborted the plugin start.")
            return

        if dry_run:
            KickInactiveClients.logger.info("Dry run is enabled - logging actions intead of actually performing them.")

        idleMover = KickInactiveClients(plugin_stopper, bot.ts3conn)
        plugin_stopper.clear()
        idleMover.start()


@command(f"{plugin_command_name} stop")
def stop_plugin(_sender=None, _msg=None):
    """
    Stop the KickInactiveClients by setting the plugin_stopper signal and undefining the plugin.
    """
    global idleMover
    plugin_stopper.set()
    idleMover = None

@command(f"{plugin_command_name} restart")
def restart_plugin(_sender=None, _msg=None):
    """
    Restarts the plugin by executing the respective functions.
    """
    stop_plugin()
    start_plugin()


@setup
def setup(ts3bot, auto_start = autoStart, enable_dry_run = dry_run, frequency = check_frequency, min_idle_time_seconds = idle_time_seconds, min_clientsonline_kick_threshold = clientsonline_kick_threshold, kick_message = kick_reason_message):
    global bot, autoStart, dry_run, check_frequency, idle_time_seconds, clientsonline_kick_threshold, kick_reason_message

    bot = ts3bot
    autoStart = auto_start
    dry_run = enable_dry_run
    check_frequency = frequency
    idle_time_seconds = min_idle_time_seconds
    clientsonline_kick_threshold = min_clientsonline_kick_threshold
    kick_reason_message = kick_message

    if autoStart:
        start_plugin()


@exit
def exit_plugin():
    global idleMover

    if idleMover is not None:
        plugin_stopper.set()
        idleMover.join()
        idleMover = None
