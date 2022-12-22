# standard imports
import logging
import threading
from threading import Thread
from typing import Union
import re

# third-party imports
from ts3API.Events import ClientEnteredEvent, ClientMovedEvent, ClientMovedSelfEvent
from ts3API.TS3Connection import TS3QueryException
from ts3API.utilities import TS3Exception
from ts3API.TS3QueryExceptionType import TS3QueryExceptionType

# local imports
from module_loader import setup_plugin, exit_plugin, command, event
import teamspeak_bot

PLUGIN_VERSION = 0.1
PLUGIN_COMMAND_NAME = "privatechannelmanager"
PLUGIN_INFO: Union[None, "PrivateChannelManager"] = None
PLUGIN_STOPPER = threading.Event()
BOT: teamspeak_bot.Ts3Bot

# defaults for configureable options
AUTO_START = True
DRY_RUN = False  # log instead of performing actual actions
SERVERGROUPS_TO_EXCLUDE = None
CHANNEL_NAME = "Create own private channel"
CHANNEL_GROUP_NAME = "Channel Admin"
CHANNEL_DELETION_DELAY_SECONDS = 0


class PrivateChannelManager(Thread):
    """
    PrivateChannelManager class. Creates a channel for a client and grants the client a specific channel group.
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
        Create a new PrivateChannelManager object.
        :param stop_event: Event to signalize the PrivateChannelManager to stop moving.
        :type stop_event: threading.Event
        :param ts3conn: Connection to use
        :type: TS3Connection
        """
        Thread.__init__(self)
        self.stopped = stop_event
        self.ts3conn = ts3conn
        self.update_servergroup_ids_list()

        self.creation_channel_id = None
        self.creation_channel_id = self.get_channel_by_name(CHANNEL_NAME)
        if self.creation_channel_id is None:
            PrivateChannelManager.logger.error(
                "Could not find any channel with the name `%s`.", str(CHANNEL_NAME)
            )

        self.channel_group_id = None
        self.channel_group_id = self.get_channel_group_by_name(CHANNEL_GROUP_NAME)
        if self.channel_group_id is None:
            PrivateChannelManager.logger.error(
                "Could not find any channel group with the name `%s`.",
                str(CHANNEL_GROUP_NAME),
            )

    def get_channel_by_name(self, name="Create your own channel"):
        """
        Get the channel id of the channel specified by name.
        :param name: Channel name
        :return: Channel id
        """
        try:
            channel_id = self.ts3conn.channelfind(name)[0].get("cid", "-1")
        except TS3Exception:
            PrivateChannelManager.logger.exception(
                "Error while finding a channel with the name `%s`.", str(name)
            )
            raise

        return channel_id

    def get_channel_group_by_name(self, name="Channel Admin"):
        """
        Get the channel group id of the channel group specified by name.
        :param name: Channel group name
        :return: Channel group id
        """
        try:
            channel_group_list = self.ts3conn._parse_resp_to_list_of_dicts(
                self.ts3conn._send("channelgrouplist")
            )
        except TS3Exception:
            PrivateChannelManager.logger.exception(
                "Error while getting the list of available channel groups."
            )
            raise

        channel_group_id = None
        for channel_group in channel_group_list:
            if int(channel_group.get("type")) in (0, 2):
                PrivateChannelManager.logger.debug(
                    "Ignoring channel group of the type 0 (template) or 2 (query)."
                )
                continue

            if not re.search(name, channel_group.get("name")):
                continue

            channel_group_id = int(channel_group.get("cgid"))
            break

        return channel_group_id

    def update_servergroup_ids_list(self):
        """
        Updates the list of servergroup IDs, which should be ignored.
        """
        self.servergroup_ids_to_ignore = []

        if SERVERGROUPS_TO_EXCLUDE is None:
            PrivateChannelManager.logger.debug(
                "No servergroups to exclude defined. Nothing todo."
            )
            return

        try:
            servergroup_list = self.ts3conn.servergrouplist()
        except TS3QueryException:
            PrivateChannelManager.logger.exception(
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
            PrivateChannelManager.logger.exception(
                "Failed to get the list of assigned servergroups for the client cldbid=%s.",
                int(cldbid),
            )
            return client_servergroup_ids

        for servergroup in client_servergroups:
            client_servergroup_ids.append(servergroup.get("sgid"))

        PrivateChannelManager.logger.debug(
            "client_database_id=%s has these servergroups: %s",
            int(cldbid),
            str(client_servergroup_ids),
        )

        return client_servergroup_ids

    def create_channel(self, client=None):
        """
        Creates a channel and grants a specific client channel admin permissions.
        """
        if client is None:
            PrivateChannelManager.logger.debug(
                "No client has been provided. Nothing todo!"
            )
            return

        PrivateChannelManager.logger.debug(
            "Received an event for this client: %s", str(client)
        )

        try:
            client_info = self.ts3conn.clientinfo(client.clid)
        except AttributeError:
            PrivateChannelManager.logger.exception(
                "The client has no clid: %s.", str(client)
            )
            raise
        except TS3Exception:
            PrivateChannelManager.logger.exception(
                "Failed to get the client info of clid=%s.", int(client.clid)
            )
            raise

        if int(client.target_channel_id) is not int(self.creation_channel_id):
            PrivateChannelManager.logger.debug(
                "The client did not join the channel, which creates new channels."
            )
            return

        if SERVERGROUPS_TO_EXCLUDE is not None:
            for client_servergroup_id in self.get_servergroups_by_client(
                client.client_dbid
            ):
                if client_servergroup_id in self.servergroup_ids_to_ignore:
                    PrivateChannelManager.logger.debug(
                        "The client is in the servergroup sgid=%s, which should be ignored: %s",
                        int(client_servergroup_id),
                        str(client),
                    )
                    return

        PrivateChannelManager.logger.info(
            "client_nickname=%s requested an own channel.",
            str(client_info.get("client_nickname")),
        )

        channel_properties = []
        channel_properties.append("channel_flag_semi_permanent=1")
        channel_properties.append(f"cpid={int(self.creation_channel_id)}")
        channel_properties.append(
            f"channel_name=Private channel from {client_info.get('client_nickname')}"
        )

        if DRY_RUN:
            PrivateChannelManager.logger.info(
                "I would have created the following channel, when dry-run would be disabled: %s",
                str(channel_properties),
            )
        else:
            PrivateChannelManager.logger.info(
                "Creating the following channel: %s",
                str(channel_properties),
            )
            try:
                recently_created_channel = self.ts3conn._parse_resp_to_dict(
                    self.ts3conn._send("channelcreate", channel_properties)
                )
            except TS3QueryException:
                PrivateChannelManager.logger.exception("Failed to create the channel.")
                raise

            try:
                self.ts3conn.clientmove(
                    int(recently_created_channel.get("cid")), int(client.clid)
                )
            except TS3QueryException:
                PrivateChannelManager.logger.exception(
                    "Failed to move the client into his private channel: %s",
                    str(client),
                )
                raise

            try:
                self.ts3conn._send(
                    "setclientchannelgroup",
                    [
                        f"cgid={int(self.channel_group_id)}",
                        f"cid={int(recently_created_channel.get('cid'))}",
                        f"cldbid={int(client_info.get('client_database_id'))}",
                    ],
                )
            except TS3QueryException:
                PrivateChannelManager.logger.exception(
                    "Failed to grant the client the respective channel group."
                )
                raise

            try:
                self.ts3conn._send(
                    "channeledit",
                    [
                        f"cid={int(recently_created_channel.get('cid'))}",
                        "channel_flag_semi_permanent=0",
                        f"channel_delete_delay={int(CHANNEL_DELETION_DELAY_SECONDS)}",
                    ],
                )
            except TS3QueryException:
                PrivateChannelManager.logger.exception(
                    "Failed to make the channel temporary."
                )
                raise


@event(ClientEnteredEvent, ClientMovedEvent, ClientMovedSelfEvent)
def client_joined(event_data):
    """
    Client joined the server or a channel or somebody moved the client into a different channel.
    """
    if PLUGIN_INFO is not None:
        PrivateChannelManager.create_channel(self=PLUGIN_INFO, client=event_data)


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
        PrivateChannelManager.logger.exception(
            "Error while sending the plugin version as a message to the client!"
        )


@command(f"{PLUGIN_COMMAND_NAME} start")
def start_plugin(_sender=None, _msg=None):
    """
    Start the PrivateChannelManager by clearing the PLUGIN_STOPPER signal and starting the mover.
    """
    global PLUGIN_INFO
    if PLUGIN_INFO is None:
        if DRY_RUN:
            PrivateChannelManager.logger.info(
                "Dry run is enabled - logging actions intead of actually performing them."
            )

        PLUGIN_INFO = PrivateChannelManager(PLUGIN_STOPPER, BOT.ts3conn)
        PLUGIN_STOPPER.clear()
        PLUGIN_INFO.start()


@command(f"{PLUGIN_COMMAND_NAME} stop")
def stop_plugin(_sender=None, _msg=None):
    """
    Stop the PrivateChannelManager by setting the PLUGIN_STOPPER signal and undefining the mover.
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
def setup(
    ts3bot,
    auto_start=AUTO_START,
    enable_dry_run=DRY_RUN,
    exclude_servergroups=SERVERGROUPS_TO_EXCLUDE,
    channel_name=CHANNEL_NAME,
    channel_group_name=CHANNEL_GROUP_NAME,
    channel_deletion_delay_seconds=CHANNEL_DELETION_DELAY_SECONDS,
):
    """
    Sets up this plugin.
    """
    global BOT, AUTO_START, DRY_RUN, SERVERGROUPS_TO_EXCLUDE, CHANNEL_NAME, CHANNEL_GROUP_NAME, CHANNEL_DELETION_DELAY_SECONDS

    BOT = ts3bot
    AUTO_START = auto_start
    DRY_RUN = enable_dry_run
    SERVERGROUPS_TO_EXCLUDE = exclude_servergroups
    CHANNEL_NAME = channel_name
    CHANNEL_GROUP_NAME = channel_group_name
    CHANNEL_DELETION_DELAY_SECONDS = channel_deletion_delay_seconds

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
