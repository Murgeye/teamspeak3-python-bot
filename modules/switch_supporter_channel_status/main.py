# standard imports
import logging
import threading
from threading import Thread
from typing import Union
import re

# third-party imports
from ts3API.Events import (
    ClientEnteredEvent,
    ClientLeftEvent,
    ClientMovedEvent,
    ClientMovedSelfEvent,
)
from ts3API.TS3Connection import TS3QueryException
from ts3API.utilities import TS3Exception

# local imports
from module_loader import setup_plugin, exit_plugin, command, event
import teamspeak_bot

PLUGIN_VERSION = 0.2
PLUGIN_COMMAND_NAME = "switchsupporterchannelstatus"
PLUGIN_INFO: Union[None, "SwitchSupporterChannelStatus"] = None
PLUGIN_STOPPER = threading.Event()
BOT: teamspeak_bot.Ts3Bot

# defaults for configureable options
AUTO_START = True
DRY_RUN = False  # log instead of performing actual actions
SUPPORTER_CHANNEL_NAME = "Support Lobby"
SERVERGROUPS_TO_CHECK = None
MINIMUM_ONLINE_CLIENTS = 1
AFK_CHANNEL_NAME = None


class SwitchSupporterChannelStatus(Thread):
    """
    SwitchSupporterChannelStatus class. Marks a supporter channel as OPEN/CLOSED when clients of specific servergroups are online/offline.
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
        Create a new SwitchSupporterChannelStatus object.
        :param stop_event: Event to signalize the SwitchSupporterChannelStatus to stop.
        :type stop_event: threading.Event
        :param ts3conn: Connection to use
        :type: TS3Connection
        """
        Thread.__init__(self)
        self.stopped = stop_event
        self.ts3conn = ts3conn

        self.supporter_channel_id = None
        self.supporter_channel_id = self.get_channel_by_name(SUPPORTER_CHANNEL_NAME)
        if self.supporter_channel_id is None:
            SwitchSupporterChannelStatus.logger.error(
                "Could not find any channel with the name `%s`.",
                str(SUPPORTER_CHANNEL_NAME),
            )

        self.afk_channel_id = None
        if AFK_CHANNEL_NAME is not None:
            self.afk_channel_id = self.get_channel_by_name(AFK_CHANNEL_NAME)
            if self.afk_channel_id is None:
                SwitchSupporterChannelStatus.logger.error(
                    "Could not find any channel with the name `%s`.",
                    str(AFK_CHANNEL_NAME),
                )

        self.servergroup_ids_to_check = None
        self.servergroup_ids_to_check = self.update_servergroup_ids_to_check()
        if self.servergroup_ids_to_check is None:
            SwitchSupporterChannelStatus.logger.error(
                "Could not find any servergroups to check for online clients."
            )

        self.client_database_ids_to_check = None
        self.client_database_ids_to_check = self.update_servergroup_member_list()
        if self.client_database_ids_to_check is None:
            SwitchSupporterChannelStatus.logger.error(
                "Seems like as your specified servergroups are empty. Could not find any members of these groups."
            )

        self.afk_clients = []

        self.available_supporter_clients = []

        self.check_all_connected_clients()

    def get_channel_by_name(self, name="Support Lobby"):
        """
        Get the channel id of the channel specified by name.
        :param name: Channel name
        :return: Channel ID
        """
        try:
            channel_id = self.ts3conn.channelfind(name)[0].get("cid", "-1")
        except TS3Exception:
            SwitchSupporterChannelStatus.logger.exception(
                "Error while finding a channel with the name `%s`.", str(name)
            )
            raise

        return channel_id

    def update_servergroup_ids_to_check(self):
        """
        Updates the list of servergroup IDs, which should be checked for clients.
        :returns: List of servergroup IDs, matching the configured servergroup name pattern.
        """
        servergroup_ids = []
        if SERVERGROUPS_TO_CHECK is None:
            SwitchSupporterChannelStatus.logger.error(
                "No servergroups to check were defined."
            )
            raise ValueError

        try:
            servergroup_list = self.ts3conn.servergrouplist()
        except TS3QueryException:
            SwitchSupporterChannelStatus.logger.exception(
                "Failed to get the list of available servergroups."
            )

        for servergroup in servergroup_list:
            if servergroup.get("name") in SERVERGROUPS_TO_CHECK.split(","):
                servergroup_ids.append(servergroup.get("sgid"))

        return servergroup_ids

    def update_servergroup_member_list(self):
        """
        Updates the list of client database IDs, which should be checked for online/offline.
        :returns: List of client database IDs, which are member of the servergroups.
        """
        servergroupclient_list = []

        try:
            for servergroup_id in self.servergroup_ids_to_check:
                servergroupclient_list.append(
                    self.ts3conn._parse_resp_to_list_of_dicts(
                        self.ts3conn._send(
                            "servergroupclientlist", [f"sgid={servergroup_id}"]
                        )
                    )
                )
        except TS3QueryException:
            SwitchSupporterChannelStatus.logger.exception(
                "Failed to get the client list of the servergroup sgid=%s.",
                int(servergroup_id),
            )
            raise

        client_database_ids = []
        for client_list in servergroupclient_list:
            for client in client_list:
                client_database_ids.append(client.get("cldbid"))

        return client_database_ids

    def check_all_connected_clients(self):
        """
        Checks all connected clients and opens/closes the supporter channel respectively.
        """
        try:
            client_list = self.ts3conn.clientlist()
        except TS3QueryException:
            SwitchSupporterChannelStatus.logger.exception(
                "Failed to get the client list."
            )
            raise

        for connected_client in client_list:
            self.update_available_supporter_client_list(connected_client.get("clid"))

        self.open_or_close_supporter_channel()

    def update_available_supporter_client_list(self, client_id):
        """
        Updates the available supporter client list in order to decide how many supporters are available or not.
        :param: client_id: A client ID (clid)
        """
        try:
            client_info = self.ts3conn.clientinfo(int(client_id))
        except TS3QueryException:
            SwitchSupporterChannelStatus.logger.exception(
                "Failed to get the client list."
            )
            raise

        if int(client_info.get("client_type")) == 1:
            SwitchSupporterChannelStatus.logger.debug(
                "Ignoring ServerQuery client: client_database_id=%s, client_nickname=%s",
                client_info.get("client_database_id"),
                client_info.get("client_nickname"),
            )
            return

        if (
            client_info.get("client_database_id")
            not in self.client_database_ids_to_check
        ):
            if int(client_id) in self.available_supporter_clients:
                self.available_supporter_clients.remove(int(client_id))

            SwitchSupporterChannelStatus.logger.debug(
                "Skipping client, which is not member of any servergroup, which I should check: client_database_id=%s, client_nickname=%s",
                client_info.get("client_database_id"),
                client_info.get("client_nickname"),
            )
            return

        if int(client_id) not in self.available_supporter_clients:
            self.available_supporter_clients.append(int(client_id))

        if self.afk_channel_id is not None:
            if int(client_info.get("cid")) == int(self.afk_channel_id):
                if int(client_id) in self.available_supporter_clients:
                    self.available_supporter_clients.remove(int(client_id))

    def open_or_close_supporter_channel(self):
        """
        Opens or closes a specific channel, when clients of specific servergroups are online or offline.
        """
        try:
            channel_info = self.ts3conn._parse_resp_to_list_of_dicts(
                self.ts3conn._send(
                    "channelinfo", [f"cid={int(self.supporter_channel_id)}"]
                )
            )[0]
        except TS3Exception:
            SwitchSupporterChannelStatus.logger.exception(
                "Failed to get the channel information of the cid=%s.",
                int(self.supporter_channel_id),
            )
            raise

        original_channel_name = re.sub(
            r"\[(OPEN|CLOSED)\]", "", channel_info.get("channel_name")
        ).strip()

        channel_properties = []
        channel_properties.append(f"cid={int(self.supporter_channel_id)}")

        if len(self.available_supporter_clients) >= int(MINIMUM_ONLINE_CLIENTS):
            channel_properties.append("channel_maxclients=-1")
            channel_properties.append(f"channel_name={original_channel_name} [OPEN]")
            switch_channel_action = "open"
        else:
            channel_properties.append("channel_maxclients=0")
            channel_properties.append(f"channel_name={original_channel_name} [CLOSED]")
            switch_channel_action = "close"

        if (
            re.search(r"\[OPEN\]", channel_info.get("channel_name"))
            and switch_channel_action == "open"
        ):
            SwitchSupporterChannelStatus.logger.debug(
                "Channel is already open. Nothing todo."
            )
            return

        if (
            re.search(r"\[CLOSED\]", channel_info.get("channel_name"))
            and switch_channel_action == "close"
        ):
            SwitchSupporterChannelStatus.logger.debug(
                "Channel is already closed. Nothing todo."
            )
            return

        SwitchSupporterChannelStatus.logger.info(
            "Currently available supporters (client_database_ids): %s",
            str(self.available_supporter_clients),
        )

        if DRY_RUN:
            SwitchSupporterChannelStatus.logger.info(
                "If the dry-run would be disabled, I would have executed the following action to the supporter channel `%s`: %s (New channel properties: %s)",
                original_channel_name,
                switch_channel_action,
                str(channel_properties),
            )
        else:
            SwitchSupporterChannelStatus.logger.info(
                "Executing the following action to the supporter channel `%s`: %s",
                original_channel_name,
                switch_channel_action,
            )

            try:
                self.ts3conn._send(
                    "channeledit",
                    channel_properties,
                )
            except TS3QueryException as query_exception:
                # Error: channel name already in use
                if int(query_exception.id) == 771:
                    SwitchSupporterChannelStatus.logger.debug(
                        "The supporter channel has already the expected named."
                    )
                    return

                SwitchSupporterChannelStatus.logger.exception(
                    "Failed to %s the channel.", switch_channel_action
                )
                raise


@event(ClientEnteredEvent)
def client_joined_server(event_data):
    """
    Client joined the server.
    """
    if PLUGIN_INFO is not None:
        if int(event_data.target_channel_id) == int(PLUGIN_INFO.afk_channel_id):
            if int(event_data.client_id) not in PLUGIN_INFO.afk_clients:
                PLUGIN_INFO.afk_clients.append(int(event_data.client_id))

        SwitchSupporterChannelStatus.update_available_supporter_client_list(
            self=PLUGIN_INFO, client_id=event_data.client_id
        )
        SwitchSupporterChannelStatus.open_or_close_supporter_channel(self=PLUGIN_INFO)


@event(ClientLeftEvent)
def client_left_server(event_data):
    """
    Client left the server.
    """
    if PLUGIN_INFO is not None:
        if int(event_data.client_id) in PLUGIN_INFO.afk_clients:
            PLUGIN_INFO.afk_clients.remove(int(event_data.client_id))

        if int(event_data.client_id) in PLUGIN_INFO.available_supporter_clients:
            PLUGIN_INFO.available_supporter_clients.remove(int(event_data.client_id))

        SwitchSupporterChannelStatus.open_or_close_supporter_channel(self=PLUGIN_INFO)


@event(ClientMovedEvent, ClientMovedSelfEvent)
def client_moved_channel(event_data):
    """
    Client moved into a different channel or was moved to a different channel by someone.
    """
    if PLUGIN_INFO is not None:
        if int(event_data.target_channel_id) == int(PLUGIN_INFO.afk_channel_id):
            if int(event_data.client_id) not in PLUGIN_INFO.afk_clients:
                PLUGIN_INFO.afk_clients.append(int(event_data.client_id))
        else:
            if int(event_data.client_id) in PLUGIN_INFO.afk_clients:
                PLUGIN_INFO.afk_clients.remove(int(event_data.client_id))

        SwitchSupporterChannelStatus.update_available_supporter_client_list(
            self=PLUGIN_INFO, client_id=event_data.client_id
        )
        SwitchSupporterChannelStatus.open_or_close_supporter_channel(self=PLUGIN_INFO)


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
        SwitchSupporterChannelStatus.logger.exception(
            "Error while sending the plugin version as a message to the client!"
        )


@command(f"{PLUGIN_COMMAND_NAME} start")
def start_plugin(_sender=None, _msg=None):
    """
    Start the SwitchSupporterChannelStatus by clearing the PLUGIN_STOPPER signal and starting the plugin.
    """
    global PLUGIN_INFO
    if PLUGIN_INFO is None:
        if DRY_RUN:
            SwitchSupporterChannelStatus.logger.info(
                "Dry run is enabled - logging actions intead of actually performing them."
            )

        PLUGIN_INFO = SwitchSupporterChannelStatus(PLUGIN_STOPPER, BOT.ts3conn)
        PLUGIN_STOPPER.clear()
        PLUGIN_INFO.start()


@command(f"{PLUGIN_COMMAND_NAME} stop")
def stop_plugin(_sender=None, _msg=None):
    """
    Stop the SwitchSupporterChannelStatus by setting the PLUGIN_STOPPER signal and undefining the plugin.
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
    supporter_channel_name=SUPPORTER_CHANNEL_NAME,
    servergroups_to_check=SERVERGROUPS_TO_CHECK,
    minimum_online_clients=MINIMUM_ONLINE_CLIENTS,
    afk_channel_name=AFK_CHANNEL_NAME,
):
    """
    Sets up this plugin.
    """
    global BOT, AUTO_START, DRY_RUN, SUPPORTER_CHANNEL_NAME, SERVERGROUPS_TO_CHECK, MINIMUM_ONLINE_CLIENTS, AFK_CHANNEL_NAME

    BOT = ts3bot
    AUTO_START = auto_start
    DRY_RUN = enable_dry_run
    SUPPORTER_CHANNEL_NAME = supporter_channel_name
    SERVERGROUPS_TO_CHECK = servergroups_to_check
    MINIMUM_ONLINE_CLIENTS = minimum_online_clients
    AFK_CHANNEL_NAME = afk_channel_name

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
