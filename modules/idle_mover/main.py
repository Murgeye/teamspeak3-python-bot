# standard imports
import logging
import threading
import traceback
from threading import Thread
from typing import Union
import sys
import re

# third-party imports
from ts3API.Events import ClientLeftEvent
from ts3API.TS3Connection import TS3QueryException
from ts3API.utilities import TS3Exception

# local imports
from module_loader import setup_plugin, exit_plugin, command, event
import teamspeak_bot

PLUGIN_VERSION = 0.1
PLUGIN_COMMAND_NAME = "idlemover"
PLUGIN_INFO: Union[None, "IdleMover"] = None
PLUGIN_STOPPER = threading.Event()
BOT: teamspeak_bot.Ts3Bot

# defaults for configureable options
AUTO_START = True
DRY_RUN = False  # log instead of performing actual actions
CHECK_FREQUENCY_SECONDS = 30.0
CHANNELS_TO_EXCLUDE = None
SERVERGROUPS_TO_EXCLUDE = None
ENABLE_AUTO_MOVE_BACK = True
RESP_CHANNEL_SETTINGS = True
FALLBACK_ACTION = None
IDLE_TIME_SECONDS = 600.0
CHANNEL_NAME = "AFK"


class IdleMover(Thread):
    """
    IdleMover class. Moves clients which are idle since more than `IDLE_TIME_SECONDS` seconds to the channel `CHANNEL_NAME`.
    """

    # configure logger
    class_name = __qualname__
    logger = logging.getLogger(class_name)
    logger.propagate = 0
    logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler(f"logs/{class_name.lower()}.log", mode="a+")
    formatter = logging.Formatter("%(asctime)s: %(levelname)s: %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.info("Configured %s logger", str(class_name))
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
        self.afk_channel = self.get_channel_by_name(CHANNEL_NAME)
        self.client_channels = {}

        self.channel_ids_to_ignore = []
        self.channel_ids_to_ignore = self.update_channel_ids_list()

        self.update_servergroup_ids_list()
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
                    IdleMover.logger.debug(
                        "update_client_list ignoring ServerQuery client: %s",
                        str(client),
                    )
                    continue

                self.idle_list.append(client)

            IdleMover.logger.debug("update_idle_list: %s", str(self.idle_list))
        except TS3Exception:
            IdleMover.logger.exception("Error getting client list with times!")
            self.idle_list = []

    def update_channel_ids_list(self):
        """
        Updates the list of channel IDs, which should be ignored.
        """
        channel_ids_to_ignore = []

        if CHANNELS_TO_EXCLUDE is None:
            IdleMover.logger.debug("No channels to exclude defined. Nothing todo.")
            return channel_ids_to_ignore

        try:
            channel_list = self.ts3conn.channellist()
        except TS3QueryException:
            IdleMover.logger.exception("Failed to get the list of available channels.")

        for channel in channel_list:
            if any(
                re.search(channel_name_pattern, channel.get("channel_name"))
                for channel_name_pattern in CHANNELS_TO_EXCLUDE.split(",")
            ):
                channel_ids_to_ignore.append(channel.get("cid"))

        return channel_ids_to_ignore

    def update_servergroup_ids_list(self):
        """
        Updates the list of servergroup IDs, which should be ignored.
        """
        self.servergroup_ids_to_ignore = []

        if SERVERGROUPS_TO_EXCLUDE is None:
            IdleMover.logger.debug("No servergroups to exclude defined. Nothing todo.")
            return

        try:
            servergroup_list = self.ts3conn.servergrouplist()
        except TS3QueryException:
            IdleMover.logger.exception(
                "Failed to get the list of available servergroups."
            )

        self.servergroup_ids_to_ignore.clear()
        for servergroup in servergroup_list:
            if servergroup.get("name") in SERVERGROUPS_TO_EXCLUDE.split(","):
                self.servergroup_ids_to_ignore.append(servergroup.get("sgid"))

    def get_servergroups_by_client(self, cldbid):
        """
        Returns the list of servergroup IDs, which the client is assigned to.
        :param: cldbid: The client database ID.
        :returns: List of servergroup IDs assigned to the client.
        """
        client_servergroup_ids = []

        try:
            client_servergroups = self.ts3conn._parse_resp_to_list_of_dicts(
                self.ts3conn._send("servergroupsbyclientid", [f"cldbid={cldbid}"])
            )
        except TS3QueryException:
            IdleMover.logger.exception(
                "Failed to get the list of assigned servergroups for the client cldbid=%s.",
                int(cldbid),
            )
            return client_servergroup_ids

        for servergroup in client_servergroups:
            client_servergroup_ids.append(servergroup.get("sgid"))

        IdleMover.logger.debug(
            "client_database_id=%s has these servergroups: %s",
            int(cldbid),
            str(client_servergroup_ids),
        )

        return client_servergroup_ids

    def get_idle_list(self):
        """
        Get list of clients which are idle since more than `IDLE_TIME_SECONDS` seconds.
        :return: List of clients which are idle.
        """
        if self.idle_list is None:
            IdleMover.logger.debug("get_idle_list idle_list is None!")
            return []

        IdleMover.logger.debug(
            "get_idle_list current awaylist: %s!", str(self.idle_list)
        )

        client_idle_list = []
        for client in self.idle_list:
            IdleMover.logger.debug("get_idle_list checking client: %s", str(client))

            if "cid" not in client.keys():
                IdleMover.logger.error(
                    "get_idle_list client without cid: %s!", str(client)
                )
                continue

            if client.get("client_type") == "1":
                IdleMover.logger.debug("Ignoring ServerQuery client: %s", str(client))
                continue

            if CHANNELS_TO_EXCLUDE is not None:
                if client.get("cid") in self.channel_ids_to_ignore:
                    IdleMover.logger.debug(
                        "The client is in a channel, which should be ignored: %s",
                        str(client),
                    )
                    continue

            if SERVERGROUPS_TO_EXCLUDE is not None:
                client_is_in_group = False
                for client_servergroup_id in self.get_servergroups_by_client(
                    client.get("client_database_id")
                ):
                    if client_servergroup_id in self.servergroup_ids_to_ignore:
                        IdleMover.logger.debug(
                            "The client is in the servergroup sgid=%s, which should be ignored: %s",
                            int(client_servergroup_id),
                            str(client),
                        )
                        client_is_in_group = True
                        break

                if client_is_in_group:
                    continue

            if "client_idle_time" not in client.keys():
                IdleMover.logger.error(
                    "get_idle_list client without client_idle_time: %s!", str(client)
                )
                continue

            if int(client.get("cid", "-1")) == int(self.afk_channel):
                IdleMover.logger.debug(
                    "get_idle_list client is already in the afk_channel: %s!",
                    str(client),
                )
                continue

            if int(client.get("client_idle_time")) / 1000 <= float(IDLE_TIME_SECONDS):
                IdleMover.logger.debug(
                    "get_idle_list client is less or equal then %s seconds idle: %s!",
                    int(IDLE_TIME_SECONDS),
                    str(client),
                )
                continue

            IdleMover.logger.debug(
                "get_idle_list adding client to list: %s!", str(client)
            )
            client_idle_list.append(client)

        IdleMover.logger.debug(
            "get_idle_list updated awaylist: %s!", str(client_idle_list)
        )

        return client_idle_list

    def get_back_list(self):
        """
        Get list of clients which are in the afk channel, but not idle anymore.
        :return: List of clients which are not idle anymore.
        """
        if self.idle_list is None:
            IdleMover.logger.debug("get_back_list idle_list is None!")
            return []

        client_back_list = []
        for client in self.idle_list:
            IdleMover.logger.debug("get_back_list checking client: %s", str(client))

            if "cid" not in client.keys():
                IdleMover.logger.error(
                    "get_back_list client without cid: %s!", str(client)
                )
                continue

            if "client_idle_time" not in client.keys():
                IdleMover.logger.error(
                    "get_back_list client without client_idle_time: %s!", str(client)
                )
                continue

            if int(client.get("cid", "-1")) != int(self.afk_channel):
                IdleMover.logger.debug(
                    "get_back_list client is not in the afk_channel anymore: %s!",
                    str(client),
                )
                continue

            if int(client.get("client_idle_time")) / 1000 > float(IDLE_TIME_SECONDS):
                IdleMover.logger.debug(
                    "get_back_list client is greater then %s seconds idle: %s!",
                    int(IDLE_TIME_SECONDS),
                    str(client),
                )
                continue

            IdleMover.logger.debug(
                "get_back_list adding client to list: %s!", str(client)
            )
            client_back_list.append(client)

        IdleMover.logger.debug(
            "get_back_list updated client list: %s!", str(client_back_list)
        )
        return client_back_list

    def get_channel_by_name(self, name="AFK"):
        """
        Get the channel id of the channel specified by name.
        :param name: Channel name
        :return: Channel id
        """
        try:
            channel = self.ts3conn.channelfind(name)[0].get("cid", "-1")
        except TS3Exception:
            IdleMover.logger.exception(
                "Error while finding a channel with the name `%s`.", str(name)
            )
            raise
        return channel

    def move_to_afk(self):
        """
        Move clients to the `afk_channel`.
        """
        idle_list = self.get_idle_list()
        if idle_list is None:
            IdleMover.logger.debug("move_to_afk idle list is empty. Nothing todo.")
            return

        IdleMover.logger.debug("Moving clients to afk!")

        for client in idle_list:
            if DRY_RUN:
                IdleMover.logger.info("I would have moved this client: %s", str(client))
            else:
                IdleMover.logger.info(
                    "Moving the client clid=%s client_nickname=%s to afk!",
                    int(client.get("clid", "-1")),
                    str(client.get("client_nickname", "-1")),
                )
                IdleMover.logger.debug("Client: %s", str(client))

                try:
                    self.ts3conn.clientmove(
                        self.afk_channel, int(client.get("clid", "-1"))
                    )
                    self.client_channels[client.get("clid", "-1")] = client.get(
                        "cid", "0"
                    )
                except TS3Exception:
                    IdleMover.logger.exception(
                        "Error moving client! clid=%s", int(client.get("clid", "-1"))
                    )

            IdleMover.logger.debug(
                "Moved List after move: %s", str(self.client_channels)
            )

    def move_all_afk(self):
        """
        Move all idle clients.
        """
        try:
            self.move_to_afk()
        except AttributeError:
            IdleMover.logger.exception("Connection error!")

    def fallback_action(self, client_id):
        """
        In case if a client couldn't be moved, this function decides if the user should simply stay in the
        AFK channel or if he should be moved to an alternative channel.
        :param client_id: The client ID, which should be moved
        """
        if FALLBACK_ACTION is None or FALLBACK_ACTION == "None":
            return

        channel_name = str(FALLBACK_ACTION)

        try:
            self.ts3conn.clientmove(self.get_channel_by_name(channel_name), client_id)
            del self.client_channels[str(client_id)]
        except KeyError:
            IdleMover.logger.error(
                "Error moving client! clid=%s not found in %s",
                int(client_id),
                str(self.client_channels),
            )
        except TS3Exception:
            IdleMover.logger.exception("Error moving client! clid=%s", int(client_id))

    def move_all_back(self):
        """
        Move all clients who are not idle anymore.
        """
        back_list = self.get_back_list()
        if back_list is None:
            IdleMover.logger.debug("move_all_back back list is empty. Nothing todo.")
            return

        IdleMover.logger.debug("Moving clients back")
        IdleMover.logger.debug("Backlist is: %s", str(back_list))
        IdleMover.logger.debug(
            "Saved channel list keys are: %s\n", str(self.client_channels.keys())
        )

        try:
            channel_list = self.ts3conn.channellist()
        except TS3QueryException as query_exception:
            IdleMover.logger.error(
                "Failed to get the current channellist: %s",
                str(query_exception.message),
            )
            return

        for client in back_list:
            if client.get("clid", -1) not in self.client_channels:
                continue

            IdleMover.logger.info(
                "Moving the client clid=%s client_nickname=%s back!",
                int(client.get("clid", -1)),
                str(client.get("client_nickname", -1)),
            )
            IdleMover.logger.debug("Client: %s", str(client))
            IdleMover.logger.debug(
                "Saved channel list keys: %s", str(self.client_channels)
            )

            channel_id = int(self.client_channels.get(client.get("clid", -1)))
            client_id = int(client.get("clid", "-1"))

            try:
                channel_info = self.ts3conn._parse_resp_to_dict(
                    self.ts3conn._send("channelinfo", [f"cid={channel_id}"])
                )
            except TS3QueryException as query_exception:
                # Error: invalid channel ID (channel ID does not exist (anymore))
                if int(query_exception.id) == 768:
                    IdleMover.logger.error(
                        "Failed to get channelinfo as the channel does not exist anymore: %s",
                        str(client),
                    )
                    continue

            channel_details = None
            for channel in channel_list:
                if int(channel["cid"]) == channel_id:
                    channel_details = channel
                    break

            if RESP_CHANNEL_SETTINGS and channel_details is not None:
                if int(channel_info.get("channel_maxclients")) != -1 and int(
                    channel_details.get("total_clients")
                ) >= int(channel_info.get("channel_maxclients")):
                    IdleMover.logger.warning(
                        "Failed to move back the following client as the channel has already the maximum of clients: %s",
                        str(client),
                    )
                    self.fallback_action(client_id)
                    continue

                if int(channel_info.get("channel_flag_password")):
                    IdleMover.logger.warning(
                        "Failed to move back the following client as the channel has a password: %s",
                        str(client),
                    )
                    self.fallback_action(client_id)
                    continue

            try:
                self.ts3conn.clientmove(channel_id, client_id)

                del self.client_channels[str(client_id)]
            except TS3QueryException as query_exception:
                # Error: invalid channel ID (channel ID does not exist (anymore))
                if int(query_exception.id) == 768:
                    IdleMover.logger.error(
                        "Failed to move back the following client as the old channel does not exist anymore: %s",
                        str(client),
                    )
                # Error: channel maxclient or maxfamily reached
                if int(query_exception.id) in (777, 778):
                    IdleMover.logger.error(
                        "Failed to move back the following client as the old channel has already the maximum of clients: %s",
                        str(client),
                    )
                # Error: invalid channel password
                if int(query_exception.id) == 781:
                    IdleMover.logger.error(
                        "Failed to move back the following client as the old channel has an unknown password: %s",
                        str(client),
                    )
                else:
                    IdleMover.logger.exception(
                        "Failed to move back the following client: %s", str(client)
                    )

                self.fallback_action(client_id)

    def auto_move_all(self):
        """
        Loop move functions until the stop signal is sent.
        """
        while not self.stopped.wait(float(CHECK_FREQUENCY_SECONDS)):
            IdleMover.logger.debug("Afkmover running!")

            try:
                self.update_client_list()

                if ENABLE_AUTO_MOVE_BACK:
                    self.move_all_back()

                self.move_all_afk()
            except BaseException:
                IdleMover.logger.error("Uncaught exception: %s", str(sys.exc_info()[0]))
                IdleMover.logger.error(str(sys.exc_info()[1]))
                IdleMover.logger.error(traceback.format_exc())
                IdleMover.logger.error(
                    "Saved channel list keys are: %s\n",
                    str(self.client_channels.keys()),
                )

        IdleMover.logger.warning("AFKMover stopped!")
        self.client_channels = {}


@command(f"{PLUGIN_COMMAND_NAME} version")
def send_version(sender=None, _msg=None):
    """
    Sends the plugin version as textmessage to the `sender`.
    """
    try:
        teamspeak_bot.send_msg_to_client(
            BOT.ts3conn,
            sender,
            f"This plugin is installed in the version `{str(PLUGIN_VERSION)}`.",
        )
    except TS3Exception:
        IdleMover.logger.exception(
            "Error while sending the plugin version as a message to the client!"
        )


@command(f"{PLUGIN_COMMAND_NAME} start")
def start_plugin(_sender=None, _msg=None):
    """
    Start the IdleMover by clearing the PLUGIN_STOPPER signal and starting the mover.
    """
    global PLUGIN_INFO
    if PLUGIN_INFO is None:
        if DRY_RUN:
            IdleMover.logger.info(
                "Dry run is enabled - logging actions intead of actually performing them."
            )

        PLUGIN_INFO = IdleMover(PLUGIN_STOPPER, BOT.ts3conn)
        PLUGIN_STOPPER.clear()
        PLUGIN_INFO.start()


@command(f"{PLUGIN_COMMAND_NAME} stop")
def stop_plugin(_sender=None, _msg=None):
    """
    Stop the IdleMover by setting the PLUGIN_STOPPER signal and undefining the mover.
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


@event(ClientLeftEvent)
def client_left(event_data):
    """
    Clean up leaving clients.
    """
    # Forget clients that were moved to the afk channel and then left
    if PLUGIN_INFO is not None:
        if str(event_data.client_id) in PLUGIN_INFO.client_channels:
            del PLUGIN_INFO.client_channels[str(event_data.client_id)]


@setup_plugin
def setup(
    ts3bot,
    auto_start=AUTO_START,
    enable_dry_run=DRY_RUN,
    frequency=CHECK_FREQUENCY_SECONDS,
    exclude_channels=CHANNELS_TO_EXCLUDE,
    exclude_servergroups=SERVERGROUPS_TO_EXCLUDE,
    auto_move_back=ENABLE_AUTO_MOVE_BACK,
    respect_channel_settings=RESP_CHANNEL_SETTINGS,
    fallback_channel=FALLBACK_ACTION,
    min_idle_time_seconds=IDLE_TIME_SECONDS,
    channel=CHANNEL_NAME,
):
    """
    Sets up this plugin.
    """
    global BOT, AUTO_START, DRY_RUN, CHECK_FREQUENCY_SECONDS, CHANNELS_TO_EXCLUDE, SERVERGROUPS_TO_EXCLUDE, ENABLE_AUTO_MOVE_BACK, RESP_CHANNEL_SETTINGS, FALLBACK_ACTION, IDLE_TIME_SECONDS, CHANNEL_NAME

    BOT = ts3bot
    AUTO_START = auto_start
    DRY_RUN = enable_dry_run
    CHECK_FREQUENCY_SECONDS = frequency
    CHANNELS_TO_EXCLUDE = exclude_channels
    SERVERGROUPS_TO_EXCLUDE = exclude_servergroups
    ENABLE_AUTO_MOVE_BACK = auto_move_back
    RESP_CHANNEL_SETTINGS = respect_channel_settings
    FALLBACK_ACTION = fallback_channel
    IDLE_TIME_SECONDS = min_idle_time_seconds
    CHANNEL_NAME = channel

    if AUTO_START:
        start_plugin()


@exit_plugin
def afkmover_exit():
    """
    Exits this plugin gracefully.
    """
    global PLUGIN_INFO

    if PLUGIN_INFO is not None:
        PLUGIN_STOPPER.set()
        PLUGIN_INFO.join()
        PLUGIN_INFO = None
