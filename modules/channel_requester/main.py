# standard imports
import logging
import threading
from threading import Thread
from typing import Union
from copy import deepcopy
import re

# third-party imports
from ts3API.Events import ClientEnteredEvent, ClientMovedEvent, ClientMovedSelfEvent
from ts3API.TS3Connection import TS3QueryException
from ts3API.utilities import TS3Exception

# local imports
from module_loader import setup_plugin, exit_plugin, command, event
import teamspeak_bot

PLUGIN_VERSION = 0.4
PLUGIN_COMMAND_NAME = "channelrequester"
PLUGIN_INFO: Union[None, "ChannelRequester"] = None
PLUGIN_STOPPER = threading.Event()
BOT: teamspeak_bot.Ts3Bot

# defaults for configureable options
AUTO_START = True
DRY_RUN = False  # log instead of performing actual actions
SERVERGROUPS_TO_EXCLUDE = None
CHANNEL_SETTINGS = None


class ChannelRequester(Thread):
    """
    ChannelRequester class. Creates a channel, when a client requests one through a specific channel and grants the client a specific channel group.
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
        Create a new ChannelRequester object.
        :param stop_event: Event to signalize the ChannelRequester to stop moving.
        :type stop_event: threading.Event
        :param ts3conn: Connection to use
        :type: TS3Connection
        """
        Thread.__init__(self)
        self.stopped = stop_event
        self.ts3conn = ts3conn

        self.servergroup_ids_to_ignore = []
        self.servergroup_ids_to_ignore = self.update_servergroup_ids_list()

        self.channel_configs = []
        self.channel_configs = self.parse_channel_settings(CHANNEL_SETTINGS)
        if len(self.channel_configs) == 0:
            raise ValueError("This plugin requires at least one channel configuration")

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
            ChannelRequester.logger.exception(
                "Error while getting the list of available channel groups."
            )
            raise

        channel_group_id = None
        for channel_group in channel_group_list:
            if int(channel_group.get("type")) in (0, 2):
                ChannelRequester.logger.debug(
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
        servergroup_ids_to_ignore = []

        if SERVERGROUPS_TO_EXCLUDE is None:
            ChannelRequester.logger.debug(
                "No servergroups to exclude defined. Nothing todo."
            )
            return servergroup_ids_to_ignore

        try:
            servergroup_list = self.ts3conn.servergrouplist()
        except TS3QueryException:
            ChannelRequester.logger.exception(
                "Failed to get the list of available servergroups."
            )

        for servergroup in servergroup_list:
            if servergroup.get("name") in SERVERGROUPS_TO_EXCLUDE.split(","):
                servergroup_ids_to_ignore.append(servergroup.get("sgid"))

        return servergroup_ids_to_ignore

    def get_channel_by_name(self, name="Create your own channel"):
        """
        Get the channel id of the channel specified by name.
        :param name: Channel name
        :return: Channel id
        """
        try:
            channel_id = self.ts3conn.channelfind(name)[0].get("cid", "-1")
        except TS3Exception:
            ChannelRequester.logger.exception(
                "Error while finding a channel with the name `%s`.", str(name)
            )
            raise

        return channel_id

    def parse_channel_settings(self, channel_settings):
        """
        Parses the channel settings.
        :params: channel_settings: Channel settings
        """
        old_channel_alias = None
        channel_properties_dict = {}
        channel_configs = []

        for key, value in channel_settings.items():
            try:
                channel_alias, channel_setting_name = key.split(".")
            except ValueError:
                ChannelRequester.logger.exception(
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

            if channel_setting_name == "main_channel_name":
                channel_properties_dict["main_channel_cid"] = self.get_channel_by_name(
                    value
                )

            if channel_setting_name == "channel_group_name":
                channel_group_id = None
                channel_group_id = self.get_channel_group_by_name(value)
                if channel_group_id is None:
                    ChannelRequester.logger.error(
                        "Could not find any channel group with the name `%s`.",
                        str(value),
                    )
                    raise ValueError

                channel_properties_dict["channel_group_id"] = int(channel_group_id)

        channel_configs.append(deepcopy(channel_properties_dict))

        ChannelRequester.logger.info(
            "Active channel configurations: %s", str(channel_configs)
        )

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
            ChannelRequester.logger.exception(
                "Failed to get the list of assigned servergroups for the client cldbid=%s.",
                int(cldbid),
            )
            return client_servergroup_ids

        for servergroup in client_servergroups:
            client_servergroup_ids.append(servergroup.get("sgid"))

        ChannelRequester.logger.debug(
            "client_database_id=%s has these servergroups: %s",
            int(cldbid),
            str(client_servergroup_ids),
        )

        return client_servergroup_ids

    def find_channels_by_prefix(self, channel_name_prefix=None):
        """
        Finds channels with a specific prefix.
        :param: channel_name_prefix: The prefix of the channel name, which you want to search for.
        :return: List of channels
        :type: list[dict]
        """
        managed_channels_list = []

        if channel_name_prefix is None:
            return managed_channels_list

        try:
            all_channels = self.ts3conn.channellist()
        except TS3Exception:
            ChannelRequester.logger.exception("Could not get the current channel list.")
            raise

        for channel in all_channels:
            if channel.get("channel_name").startswith(channel_name_prefix):
                managed_channels_list.append(channel)

        return managed_channels_list

    def create_channel(self, client=None):
        """
        Creates a channel and grants a specific client channel admin permissions.
        """
        if client is None:
            ChannelRequester.logger.debug("No client has been provided. Nothing todo!")
            return

        ChannelRequester.logger.debug(
            "Received an event for this client: %s", str(client)
        )

        try:
            client_info = self.ts3conn.clientinfo(client.clid)
        except AttributeError:
            ChannelRequester.logger.exception(
                "The client has no clid: %s.", str(client)
            )
            raise
        except TS3Exception:
            ChannelRequester.logger.exception(
                "Failed to get the client info of clid=%s.", int(client.clid)
            )
            raise

        if not any(
            int(channel_config["main_channel_cid"]) == int(client.target_channel_id)
            for channel_config in self.channel_configs
        ):
            ChannelRequester.logger.debug(
                "The client did not join any channel, which creates new channels."
            )
            return

        if SERVERGROUPS_TO_EXCLUDE is not None:
            for client_servergroup_id in self.get_servergroups_by_client(
                int(client_info.get("client_database_id"))
            ):
                if client_servergroup_id in self.servergroup_ids_to_ignore:
                    ChannelRequester.logger.debug(
                        "The client is in the servergroup sgid=%s, which should be ignored: %s",
                        int(client_servergroup_id),
                        str(client),
                    )
                    return

        channel_configs = deepcopy(self.channel_configs)
        for channel_config in channel_configs:
            try:
                main_channel_name = channel_config.pop("main_channel_name")
                main_channel_cid = channel_config.pop("main_channel_cid")
            except KeyError:
                ChannelRequester.logger.exception(
                    "Could not retrieve the required information from the channel configuration."
                )
                continue

            try:
                channel_group_id = channel_config.pop("channel_group_id")
                channel_name = channel_config.pop("channel_name")
            except KeyError:
                default_channel_group = "Channel Admin"
                channel_group_id = None
                channel_group_id = self.get_channel_group_by_name(default_channel_group)
                if channel_group_id is None:
                    ChannelRequester.logger.error(
                        "Could not find any channel group with the name `%s`.",
                        str(default_channel_group),
                    )
                    return

                channel_name = None

            if int(main_channel_cid) == int(client.target_channel_id):
                channel_settings = channel_config
                break

        ChannelRequester.logger.info(
            "client_nickname=%s requested an own channel under the channel `%s`.",
            str(client_info.get("client_nickname")),
            str(main_channel_name),
        )

        channel_properties = []
        channel_properties.append("channel_flag_semi_permanent=1")
        channel_properties.append(f"cpid={int(main_channel_cid)}")

        if channel_name is not None:
            if re.search("%i", channel_name):
                channels_with_prefix = self.find_channels_by_prefix(
                    channel_name.replace("%i", "")
                )

                i = 1
                next_channel_name_number = None
                previous_channel_id = None
                for channel_info in channels_with_prefix:
                    channel_name_number = int(
                        channel_info["channel_name"]
                        .replace(channel_name.replace("%i", "").strip(), "")
                        .strip()
                    )

                    if channel_name_number != i:
                        next_channel_name_number = i
                        previous_channel = [
                            channel_info
                            for channel_info in channels_with_prefix
                            if channel_info["channel_name"]
                            == channel_name.replace("%i", str(i - 1))
                        ]
                        previous_channel_id = int(previous_channel[0].get("cid"))
                        break

                    i += 1

                if next_channel_name_number is None:
                    next_channel_name_number = i

                channel_name = channel_name.replace("%i", str(next_channel_name_number))

                if previous_channel_id is not None:
                    channel_properties.append(
                        f"channel_order={int(previous_channel_id)}"
                    )

            if re.search("%u", channel_name):
                channel_name = channel_name.replace(
                    "%u", client_info.get("client_nickname")
                )

            channel_properties.append(f"channel_name={channel_name}")
        else:
            channel_properties.append(
                f"channel_name={client_info.get('client_nickname')}"
            )

        channel_delete_delay = 0
        channel_permissions = []
        for key, value in channel_settings.items():
            if key == "channel_delete_delay":
                channel_delete_delay = value
                continue

            if key.startswith("channel_"):
                channel_properties.append(f"{key}={value}")
            else:
                channel_permissions.append({f"{key}": value})

        if DRY_RUN:
            ChannelRequester.logger.info(
                "I would have created the following channel, when dry-run would be disabled: %s, %s",
                str(channel_properties),
                str(channel_permissions),
            )
        else:
            ChannelRequester.logger.info(
                "Creating the following channel: %s",
                str(channel_properties),
            )
            try:
                recently_created_channel = self.ts3conn._parse_resp_to_dict(
                    self.ts3conn._send("channelcreate", channel_properties)
                )
            except TS3QueryException:
                ChannelRequester.logger.exception("Failed to create the channel.")
                raise

            if len(channel_permissions) > 0:
                ChannelRequester.logger.info(
                    "Setting the following channel permissions on the channel `%s`: %s",
                    int(recently_created_channel.get("cid")),
                    str(channel_permissions),
                )

                for permission in channel_permissions:
                    for permsid, permvalue in permission.items():
                        try:
                            self.ts3conn._send(
                                "channeladdperm",
                                [
                                    f"cid={int(recently_created_channel.get('cid'))}",
                                    f"permsid={permsid}",
                                    f"permvalue={permvalue}",
                                ],
                            )
                        except TS3QueryException:
                            ChannelRequester.logger.exception(
                                "Failed to set the channel permission `%s` for the cid=%s.",
                                str(permsid),
                                int(recently_created_channel.get("cid")),
                            )
                            raise

            try:
                self.ts3conn.clientmove(
                    int(recently_created_channel.get("cid")), int(client.clid)
                )
            except TS3QueryException:
                ChannelRequester.logger.exception(
                    "Failed to move the client into his private channel: %s",
                    str(client),
                )
                raise

            try:
                self.ts3conn._send(
                    "setclientchannelgroup",
                    [
                        f"cgid={int(channel_group_id)}",
                        f"cid={int(recently_created_channel.get('cid'))}",
                        f"cldbid={int(client_info.get('client_database_id'))}",
                    ],
                )
            except TS3QueryException:
                ChannelRequester.logger.exception(
                    "Failed to grant the client the respective channel group."
                )
                raise

            try:
                self.ts3conn._send(
                    "channeledit",
                    [
                        f"cid={int(recently_created_channel.get('cid'))}",
                        "channel_flag_semi_permanent=0",
                        f"channel_delete_delay={int(channel_delete_delay)}",
                    ],
                )
            except TS3QueryException:
                ChannelRequester.logger.exception(
                    "Failed to make the channel temporary."
                )
                raise


@event(ClientEnteredEvent, ClientMovedEvent, ClientMovedSelfEvent)
def client_joined(event_data):
    """
    Client joined the server or a channel or somebody moved the client into a different channel.
    """
    if PLUGIN_INFO is not None:
        ChannelRequester.create_channel(self=PLUGIN_INFO, client=event_data)


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
        ChannelRequester.logger.exception(
            "Error while sending the plugin version as a message to the client!"
        )


@command(f"{PLUGIN_COMMAND_NAME} start")
def start_plugin(_sender=None, _msg=None):
    """
    Start the ChannelRequester by clearing the PLUGIN_STOPPER signal and starting the mover.
    """
    global PLUGIN_INFO
    if PLUGIN_INFO is None:
        if DRY_RUN:
            ChannelRequester.logger.info(
                "Dry run is enabled - logging actions intead of actually performing them."
            )

        PLUGIN_INFO = ChannelRequester(PLUGIN_STOPPER, BOT.ts3conn)
        PLUGIN_STOPPER.clear()
        PLUGIN_INFO.start()


@command(f"{PLUGIN_COMMAND_NAME} stop")
def stop_plugin(_sender=None, _msg=None):
    """
    Stop the ChannelRequester by setting the PLUGIN_STOPPER signal and undefining the mover.
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
    **channel_settings,
):
    """
    Sets up this plugin.
    """
    global BOT, AUTO_START, DRY_RUN, SERVERGROUPS_TO_EXCLUDE, CHANNEL_SETTINGS

    BOT = ts3bot
    AUTO_START = auto_start
    DRY_RUN = enable_dry_run
    SERVERGROUPS_TO_EXCLUDE = exclude_servergroups
    CHANNEL_SETTINGS = channel_settings

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
