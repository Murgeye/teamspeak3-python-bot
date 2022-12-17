# standard imports
import logging
import threading
import traceback
from threading import Thread
from typing import Union
import sys

# third-party imports
from ts3API.TS3Connection import TS3QueryException
from ts3API.utilities import TS3Exception

# local imports
from module_loader import setup_plugin, exit_plugin, command
import teamspeak_bot

PLUGIN_VERSION = 0.1
PLUGIN_COMMAND_NAME = "kickinactiveclients"
PLUGIN_INFO: Union[None, 'KickInactiveClients'] = None
PLUGIN_STOPPER = threading.Event()
BOT: teamspeak_bot.Ts3Bot

# defaults for configureable options
AUTO_START = True
DRY_RUN = False # log instead of performing actual actions
CHECK_FREQUENCY_SECONDS = 60.0 * 5 # 300 seconds => 5 minutes
SERVERGROUPS_TO_EXCLUDE = None
IDLE_TIME_SECONDS = 60.0 * 60 * 2 # 7200 seconds => 120 minutes => 2 hours
CLIENTSONLINE_KICK_THRESHOLD = 108 # Earliest start kicking clients when e.g. 108 of 128 slots are in use
KICK_REASON_MESSAGE = "Sorry for kicking, but we need slots!"

class KickInactiveClients(Thread):
    """
    KickInactiveClients class. Kicks clients from the server which are idle since more than `IDLE_TIME_SECONDS` seconds.
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
    logger.info("Configured %s logger", str(class_name))
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
        self.update_servergroup_ids_list()
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
            self.serverinfo = []

    def update_client_list(self):
        """
        Update list of clients with idle time.
        :return: List of connected clients with their idle time.
        """
        try:
            self.idle_list = []
            for client in self.ts3conn.clientlist(["times"]):
                if int(client.get("client_type")) == 1:
                    KickInactiveClients.logger.debug("update_client_list ignoring ServerQuery client: %s", str(client))
                    continue

                self.idle_list.append(client)

            KickInactiveClients.logger.debug("update_idle_list: %s", str(self.idle_list))
        except TS3Exception:
            KickInactiveClients.logger.exception("Error getting client list with times!")
            self.idle_list = []


    def update_servergroup_ids_list(self):
        """
        Updates the list of servergroup IDs, which should be ignored.
        """
        self.servergroup_ids_to_ignore = []

        if SERVERGROUPS_TO_EXCLUDE is None:
            KickInactiveClients.logger.debug("No servergroups to exclude defined. Nothing todo.")
            return

        try:
            servergroup_list = self.ts3conn.servergrouplist()
        except TS3QueryException:
            KickInactiveClients.logger.exception("Failed to get the list of available servergroups.")

        self.servergroup_ids_to_ignore.clear()
        for servergroup in servergroup_list:
            if servergroup.get("name") in SERVERGROUPS_TO_EXCLUDE.split(','):
                self.servergroup_ids_to_ignore.append(servergroup.get("sgid"))


    def get_servergroups_by_client(self, cldbid):
        """
        Returns the list of servergroup IDs, which the client is assigned to.
        :param: cldbid: The client database ID.
        :returns: List of servergroup IDs assigned to the client.
        """
        client_servergroup_ids = []

        try:
            client_servergroups = self.ts3conn._parse_resp_to_list_of_dicts(self.ts3conn._send("servergroupsbyclientid", [f"cldbid={cldbid}"]))
        except TS3QueryException:
            KickInactiveClients.logger.exception("Failed to get the list of assigned servergroups for the client cldbid=%s.", int(cldbid))
            return client_servergroup_ids

        for servergroup in client_servergroups:
            client_servergroup_ids.append(servergroup.get("sgid"))

        KickInactiveClients.logger.debug("client_database_id=%s has these servergroups: %s", int(cldbid), str(client_servergroup_ids))

        return client_servergroup_ids


    def get_idle_list(self):
        """
        Get list of clients which are idle since more than `IDLE_TIME_SECONDS` seconds.
        :return: List of clients which are idle.
        """
        if self.idle_list is None:
            KickInactiveClients.logger.debug("get_idle_list idle_list is None!")
            return []

        KickInactiveClients.logger.debug("get_idle_list current idle_list: %s!", str(self.idle_list))

        client_idle_list = []
        for client in self.idle_list:
            KickInactiveClients.logger.debug("get_idle_list checking client: %s", str(client))

            if "cid" not in client.keys():
                KickInactiveClients.logger.error("get_idle_list client without cid: %s!", str(client))
                continue

            if "client_idle_time" not in client.keys():
                KickInactiveClients.logger.error("get_idle_list client without client_idle_time: %s!", str(client))
                continue

            if client.get("client_type") == '1':
                KickInactiveClients.logger.debug("Ignoring ServerQuery client: %s", str(client))
                continue

            if SERVERGROUPS_TO_EXCLUDE is not None:
                client_is_in_group = False
                for client_servergroup_id in self.get_servergroups_by_client(client.get("client_database_id")):
                    if client_servergroup_id in self.servergroup_ids_to_ignore:
                        KickInactiveClients.logger.debug("The client is in the servergroup sgid=%s, which should be ignored: %s", int(client_servergroup_id), str(client))
                        client_is_in_group = True
                        break

                if client_is_in_group:
                    continue

            if int(client.get("client_idle_time")) / 1000 <= float(IDLE_TIME_SECONDS):
                KickInactiveClients.logger.debug("get_idle_list client is less or equal then %s seconds idle: %s!", int(IDLE_TIME_SECONDS), str(client))
                continue

            KickInactiveClients.logger.debug("get_idle_list adding client to list: %s!", str(client))
            client_idle_list.append(client)

        KickInactiveClients.logger.debug("get_idle_list updated idle_list: %s!", str(client_idle_list))

        return client_idle_list

    def kick_all_idle_clients(self):
        """
        Kick all idle clients.
        """
        virtualserver_clientsonline = self.serverinfo.get("virtualserver_clientsonline")
        if int(virtualserver_clientsonline) < int(CLIENTSONLINE_KICK_THRESHOLD):
            KickInactiveClients.logger.debug("Only %s of %s slots used. Nothing todo.", int(virtualserver_clientsonline), int(self.serverinfo.get('virtualserver_maxclients')))
            return

        idle_list = self.get_idle_list()
        if idle_list is None:
            KickInactiveClients.logger.debug("kick_all_idle_clients idle_list is empty. Nothing todo.")
            return

        for client in idle_list:
            KickInactiveClients.logger.info("Kicking %s clients from the server!", int(len(idle_list)))

            if DRY_RUN:
                KickInactiveClients.logger.info("I would have kicked the following client from the server, when the dry-run would be disabled: %s", str(client))
            else:
                KickInactiveClients.logger.info("Kicking the following client from the server: %s", str(client))

                try:
                    self.ts3conn.clientkick(int(client.get("clid", '-1')), 5, KICK_REASON_MESSAGE)
                except TS3Exception:
                    KickInactiveClients.logger.exception("Error kicking client clid=%s!", int(client.get('clid', '-1')))

    def loop_until_stopped(self):
        """
        Loop move functions until the stop signal is sent.
        """
        while not self.stopped.wait(float(CHECK_FREQUENCY_SECONDS)):
            KickInactiveClients.logger.debug("Thread running!")

            try:
                self.get_serverinfo()
                self.update_client_list()
                self.kick_all_idle_clients()
            except BaseException:
                KickInactiveClients.logger.error("Uncaught exception: %s", str(sys.exc_info()[0]))
                KickInactiveClients.logger.error(str(sys.exc_info()[1]))
                KickInactiveClients.logger.error(traceback.format_exc())

        KickInactiveClients.logger.warning("Thread stopped!")
        self.client_channels = {}


@command(f"{PLUGIN_COMMAND_NAME} version")
def send_version(sender=None, _msg=None):
    """
    Sends the plugin version as textmessage to the `sender`.
    """
    try:
        teamspeak_bot.send_msg_to_client(BOT.ts3conn, sender, f"This plugin is installed in the version `{str(PLUGIN_VERSION)}`.")
    except TS3Exception:
        KickInactiveClients.logger.exception("Error while sending the plugin version as a message to the client!")


@command(f"{PLUGIN_COMMAND_NAME} start")
def start_plugin(_sender=None, _msg=None):
    """
    Start the KickInactiveClients by clearing the PLUGIN_STOPPER signal and starting the plugin.
    """
    global PLUGIN_INFO
    if PLUGIN_INFO is None:
        if len(KICK_REASON_MESSAGE) > 40:
            KickInactiveClients.logger.error("The `kick_message` has %s characters, but only 40 are supported! Aborted the plugin start.", int(len(KICK_REASON_MESSAGE)))
            return

        if DRY_RUN:
            KickInactiveClients.logger.info("Dry run is enabled - logging actions intead of actually performing them.")

        PLUGIN_INFO = KickInactiveClients(PLUGIN_STOPPER, BOT.ts3conn)
        PLUGIN_STOPPER.clear()
        PLUGIN_INFO.start()


@command(f"{PLUGIN_COMMAND_NAME} stop")
def stop_plugin(_sender=None, _msg=None):
    """
    Stop the KickInactiveClients by setting the PLUGIN_STOPPER signal and undefining the plugin.
    """
    global PLUGIN_INFO
    PLUGIN_STOPPER.set()
    PLUGIN_INFO = None

@command(f"{PLUGIN_COMMAND_NAME} restart")
def restart_plugin(_sender=None, _msg=None):
    """
    Restarts the plugin by executing the respective functions.
    """
    stop_plugin()
    start_plugin()


@setup_plugin
def setup(ts3bot,
            auto_start = AUTO_START,
            enable_dry_run = DRY_RUN,
            frequency = CHECK_FREQUENCY_SECONDS,
            exclude_servergroups = SERVERGROUPS_TO_EXCLUDE,
            min_idle_time_seconds = IDLE_TIME_SECONDS,
            min_clientsonline_kick_threshold = CLIENTSONLINE_KICK_THRESHOLD,
            kick_message = KICK_REASON_MESSAGE
    ):
    """
    Sets up this plugin.
    """
    global BOT, AUTO_START, DRY_RUN, CHECK_FREQUENCY_SECONDS, SERVERGROUPS_TO_EXCLUDE, IDLE_TIME_SECONDS, CLIENTSONLINE_KICK_THRESHOLD, KICK_REASON_MESSAGE

    BOT = ts3bot
    AUTO_START = auto_start
    DRY_RUN = enable_dry_run
    CHECK_FREQUENCY_SECONDS = frequency
    SERVERGROUPS_TO_EXCLUDE = exclude_servergroups
    IDLE_TIME_SECONDS = min_idle_time_seconds
    CLIENTSONLINE_KICK_THRESHOLD = min_clientsonline_kick_threshold
    KICK_REASON_MESSAGE = kick_message

    if AUTO_START:
        start_plugin()


@exit_plugin
def exit_module():
    """
    Exits this plugin gracefully.
    """
    global PLUGIN_INFO

    if PLUGIN_INFO is not None:
        PLUGIN_STOPPER.set()
        PLUGIN_INFO.join()
        PLUGIN_INFO = None
