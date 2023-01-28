# standard imports
import logging
import threading
import traceback
from threading import Thread
from typing import Union
import sys
import re
from copy import deepcopy

# third-party imports
from ts3API.Events import ClientLeftEvent
from ts3API.TS3Connection import TS3QueryException
from ts3API.utilities import TS3Exception

# local imports
from module_loader import setup_plugin, exit_plugin, command, event
import teamspeak_bot

PLUGIN_VERSION = 0.2
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
CHANNEL_SETTINGS = None


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
        if self.afk_channel is None:
            IdleMover.logger.error("Could not get afk channel")

        self.channel_ids_to_ignore = []
        self.channel_ids_to_ignore = self.update_channel_ids_list()

        self.servergroup_ids_to_ignore = []
        self.servergroup_ids_to_ignore = self.update_servergroup_ids_list()

        self.channel_configs = []
        self.channel_configs = self.parse_channel_settings(CHANNEL_SETTINGS)

        self.idling_clients = {}

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
        client_list = []

        try:
            clientlist_with_idletimes = self.ts3conn.clientlist(["times"])
        except TS3Exception:
            IdleMover.logger.exception("Error getting client list with times!")
            raise

        for client in clientlist_with_idletimes:
            if int(client.get("client_type")) == 1:
                IdleMover.logger.debug(
                    "update_client_list ignoring ServerQuery client: %s",
                    str(client),
                )
                continue

            client_list.append(client)

        IdleMover.logger.debug(
            "Updated client list with idle times: %s", str(client_list)
        )

        return client_list

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
        servergroup_ids_to_ignore = []

        if SERVERGROUPS_TO_EXCLUDE is None:
            IdleMover.logger.debug("No servergroups to exclude defined. Nothing todo.")
            return servergroup_ids_to_ignore

        try:
            servergroup_list = self.ts3conn.servergrouplist()
        except TS3QueryException:
            IdleMover.logger.exception(
                "Failed to get the list of available servergroups."
            )

        for servergroup in servergroup_list:
            if servergroup.get("name") in SERVERGROUPS_TO_EXCLUDE.split(","):
                servergroup_ids_to_ignore.append(servergroup.get("sgid"))

        return servergroup_ids_to_ignore

    def parse_channel_settings(self, channel_settings):
        """
        Parses the channel settings.
        :params: channel_settings: Channel settings
        """
        old_channel_alias = None
        channel_properties_dict = {}
        channel_configs = []

        if len(channel_settings) == 0:
            return channel_configs

        for key, value in channel_settings.items():
            try:
                channel_alias, channel_setting_name = key.split(".")
            except ValueError:
                IdleMover.logger.exception(
                    "Failed to get channel alias and setting name. Please ensure, that your plugin configuration is valid."
                )
                raise

            if old_channel_alias is None:
                old_channel_alias = channel_alias

            if channel_alias != old_channel_alias and len(channel_properties_dict) > 0:
                old_channel_alias = channel_alias
                channel_configs.append(deepcopy(channel_properties_dict))
                channel_properties_dict.clear()

            channel_properties_dict[channel_setting_name] = value

            if channel_setting_name == "channel_name":
                channel_properties_dict["channel_id"] = self.get_channel_by_name(value)

        channel_configs.append(deepcopy(channel_properties_dict))

        for config in channel_configs:
            if not all(
                key in config for key in ("channel_name", "min_idle_time_seconds")
            ):
                raise ValueError(
                    f"The channel config `{str(config['channel_name'])}` is invalid. Both options must be defined: channel_name, min_idle_time_seconds"
                )

        IdleMover.logger.info("Active channel configurations: %s", str(channel_configs))

        return channel_configs

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
        client_idle_list = []

        client_list = self.update_client_list()

        if len(client_list) == 0:
            IdleMover.logger.debug(
                "No client is connected to the server. Nothing todo."
            )
            return client_idle_list

        IdleMover.logger.debug(
            "get_idle_list current idle list: %s!", str(self.idling_clients)
        )

        for client in client_list:
            IdleMover.logger.debug("get_idle_list checking client: %s", str(client))

            if not all(key in client.keys() for key in ("client_idle_time", "cid")):
                IdleMover.logger.warning(
                    "get_idle_list client is either missing `client_idle_time` or `cid`: %s!",
                    str(client),
                )
                continue

            client_cid = client.get("cid", "-1")

            if int(client_cid) == int(self.afk_channel):
                IdleMover.logger.debug(
                    "get_idle_list client is already in the afk_channel: %s!",
                    str(client),
                )
                continue

            if CHANNELS_TO_EXCLUDE is not None:
                if client_cid in self.channel_ids_to_ignore:
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

            try:
                channel_config = [
                    conf
                    for conf in self.channel_configs
                    if int(conf["channel_id"]) == int(client_cid)
                ][0]
            except IndexError:
                channel_config = None

            if channel_config is None:
                min_idle_time_seconds = float(IDLE_TIME_SECONDS)
            else:
                min_idle_time_seconds = float(channel_config["min_idle_time_seconds"])

            if int(client.get("client_idle_time")) / 1000 < float(
                min_idle_time_seconds
            ):
                IdleMover.logger.debug(
                    "get_idle_list client is less then %s seconds idle: %s!",
                    int(IDLE_TIME_SECONDS),
                    str(client),
                )
                continue

            IdleMover.logger.debug(
                "get_idle_list adding client to list: %s!", str(client)
            )
            client_idle_list.append(client)

        IdleMover.logger.debug(
            "get_idle_list updated idle list: %s!", str(client_idle_list)
        )

        return client_idle_list

    def get_back_list(self):
        """
        Get list of clients which are in the afk channel, but not idle anymore.
        :return: List of clients which are not idle anymore.
        """
        client_back_list = {}

        if len(self.idling_clients) == 0:
            IdleMover.logger.debug("get_back_list idle_list is None!")
            return client_back_list

        for client_clid, client_cid in self.idling_clients.items():
            IdleMover.logger.debug(
                "get_back_list checking client clid=%s", int(client_clid)
            )

            try:
                client_info = self.ts3conn.clientinfo(client_clid)
            except TS3Exception:
                IdleMover.logger.exception(
                    "Failed to get the client info of clid=%s.", int(client_clid)
                )
                raise

            if not all(
                key in client_info.keys() for key in ("client_idle_time", "cid")
            ):
                IdleMover.logger.warning(
                    "get_back_list client is either missing `client_idle_time` or `cid`: %s!",
                    str(client_info),
                )
                continue

            if int(client_info.get("cid", "-1")) != int(self.afk_channel):
                IdleMover.logger.debug(
                    "get_back_list client is not in the afk_channel anymore: client_database_id=%s, client_nickname=%s!",
                    int(client_info.get("client_database_id")),
                    str(client_info.get("client_nickname")),
                )
                del self.idling_clients[int(client_clid)]
                continue

            try:
                channel_config = [
                    conf
                    for conf in self.channel_configs
                    if int(conf["channel_id"]) == int(client_cid)
                ][0]
            except IndexError:
                channel_config = None

            if channel_config is None:
                min_idle_time_seconds = float(IDLE_TIME_SECONDS)
            else:
                min_idle_time_seconds = float(channel_config["min_idle_time_seconds"])

            if int(client_info.get("client_idle_time")) / 1000 > float(
                min_idle_time_seconds
            ):
                IdleMover.logger.debug(
                    "get_back_list client is greater then %s seconds idle: client_database_id=%s, client_nickname=%s!",
                    int(IDLE_TIME_SECONDS),
                    int(client_info.get("client_database_id")),
                    str(client_info.get("client_nickname")),
                )
                continue

            IdleMover.logger.debug(
                "get_back_list adding client to list: client_database_id=%s, client_nickname=%s!",
                int(client_info.get("client_database_id")),
                str(client_info.get("client_nickname")),
            )
            client_back_list[int(client_clid)] = int(client_cid)

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

        if len(idle_list) == 0:
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
                except TS3Exception:
                    IdleMover.logger.exception(
                        "Error moving client! clid=%s", int(client.get("clid", "-1"))
                    )

                self.idling_clients[int(client.get("clid", "-1"))] = int(
                    client.get("cid", "0")
                )

        IdleMover.logger.debug("Idling clients: %s", str(self.idling_clients))

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
            del self.idling_clients[int(client_id)]
        except KeyError:
            IdleMover.logger.error(
                "Error moving client! clid=%s not found in %s",
                int(client_id),
                str(self.idling_clients),
            )
        except TS3Exception:
            IdleMover.logger.exception("Error moving client! clid=%s", int(client_id))

    def move_all_back(self):
        """
        Move all clients who are not idle anymore.
        """
        back_list = self.get_back_list()
        if len(back_list) == 0:
            IdleMover.logger.debug("move_all_back back list is empty. Nothing todo.")
            return

        IdleMover.logger.debug("Moving clients back")
        IdleMover.logger.debug("Backlist is: %s", str(back_list))
        IdleMover.logger.debug(
            "Saved client idle list keys are: %s\n", str(self.idling_clients.keys())
        )

        try:
            channel_list = self.ts3conn.channellist()
        except TS3QueryException as query_exception:
            IdleMover.logger.error(
                "Failed to get the current channellist: %s",
                str(query_exception.message),
            )
            return

        for client_clid, client_cid in back_list.items():
            IdleMover.logger.info(
                "Moving the client clid=%s back!",
                int(client_clid),
            )

            try:
                channel_info = self.ts3conn._parse_resp_to_dict(
                    self.ts3conn._send("channelinfo", [f"cid={int(client_cid)}"])
                )
            except TS3QueryException as query_exception:
                # Error: invalid channel ID (channel ID does not exist (anymore))
                if int(query_exception.id) == 768:
                    IdleMover.logger.error(
                        "Failed to get channelinfo as the channel cid=%s does not exist anymore.",
                        int(client_cid),
                    )
                    continue

            channel_details = None
            for channel in channel_list:
                if int(channel["cid"]) == int(client_cid):
                    channel_details = channel
                    break

            if RESP_CHANNEL_SETTINGS and channel_details is not None:
                if int(channel_info.get("channel_maxclients")) != -1 and int(
                    channel_details.get("total_clients")
                ) >= int(channel_info.get("channel_maxclients")):
                    IdleMover.logger.warning(
                        "Failed to move back the following client clid=%s as the channel cid=%s has already the maximum of clients.",
                        int(client_clid),
                        int(client_cid),
                    )
                    self.fallback_action(client_clid)
                    continue

                if int(channel_info.get("channel_flag_password")):
                    IdleMover.logger.warning(
                        "Failed to move back the following client clid=%s as the channel cid=%s has a password.",
                        int(client_clid),
                        int(client_cid),
                    )
                    self.fallback_action(client_clid)
                    continue

            try:
                self.ts3conn.clientmove(client_cid, client_clid)

                del self.idling_clients[int(client_clid)]
            except TS3QueryException as query_exception:
                # Error: invalid channel ID (channel ID does not exist (anymore))
                if int(query_exception.id) == 768:
                    IdleMover.logger.error(
                        "Failed to move back the following client clid=%s as the old channel cid=%s does not exist anymore.",
                        int(client_clid),
                        int(client_cid),
                    )
                # Error: channel maxclient or maxfamily reached
                if int(query_exception.id) in (777, 778):
                    IdleMover.logger.error(
                        "Failed to move back the following client clid=%s as the old channel cid=%s has already the maximum of clients.",
                        int(client_clid),
                        int(client_cid),
                    )
                # Error: invalid channel password
                if int(query_exception.id) == 781:
                    IdleMover.logger.error(
                        "Failed to move back the following client clid=%s as the old channel cid=%s has an unknown password.",
                        int(client_clid),
                        int(client_cid),
                    )
                else:
                    IdleMover.logger.exception(
                        "Failed to move back the following client clid=%s",
                        int(client_clid),
                    )

                self.fallback_action(client_clid)

    def auto_move_all(self):
        """
        Loop move functions until the stop signal is sent.
        """
        while not self.stopped.wait(float(CHECK_FREQUENCY_SECONDS)):
            IdleMover.logger.debug("Plugin running!")

            try:
                if ENABLE_AUTO_MOVE_BACK:
                    self.move_all_back()

                self.move_all_afk()
            except BaseException:
                IdleMover.logger.error("Uncaught exception: %s", str(sys.exc_info()[0]))
                IdleMover.logger.error(str(sys.exc_info()[1]))
                IdleMover.logger.error(traceback.format_exc())

        IdleMover.logger.warning("Plugin stopped!")


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
        if str(event_data.client_id) in PLUGIN_INFO.idling_clients:
            del PLUGIN_INFO.idling_clients[int(event_data.client_id)]


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
    **channel_settings,
):
    """
    Sets up this plugin.
    """
    global BOT, AUTO_START, DRY_RUN, CHECK_FREQUENCY_SECONDS, CHANNELS_TO_EXCLUDE, SERVERGROUPS_TO_EXCLUDE, ENABLE_AUTO_MOVE_BACK, RESP_CHANNEL_SETTINGS, FALLBACK_ACTION, IDLE_TIME_SECONDS, CHANNEL_NAME, CHANNEL_SETTINGS

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
    CHANNEL_SETTINGS = channel_settings

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
