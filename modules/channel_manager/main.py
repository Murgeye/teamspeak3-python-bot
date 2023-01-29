# standard imports
import logging
import threading
from threading import Thread
from typing import Union
from copy import deepcopy

# third-party imports
from ts3API.Events import (
    ClientEnteredEvent,
    ClientLeftEvent,
    ClientMovedEvent,
    ClientMovedSelfEvent,
    ClientKickedEvent,
    ClientBannedEvent,
)
from ts3API.utilities import TS3Exception, TS3QueryException

# local imports
from module_loader import setup_plugin, exit_plugin, command, event
import teamspeak_bot

PLUGIN_VERSION = 0.3
PLUGIN_COMMAND_NAME = "channelmanager"
PLUGIN_INFO: Union[None, "ChannelManager"] = None
PLUGIN_STOPPER = threading.Event()
BOT: teamspeak_bot.Ts3Bot

# defaults for configureable options
AUTO_START = True
DRY_RUN = False  # log instead of performing actual actions
CHANNEL_SETTINGS = None


class ChannelManager(Thread):
    """
    ChannelManager class. Automatically creates channels, when necessary.
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
        Create a new ChannelManager object.
        :param stop_event: Event to signalize the ChannelManager to stop.
        :type stop_event: threading.Event
        :param ts3conn: Connection to use
        :type: TS3Connection
        """
        Thread.__init__(self)
        self.stopped = stop_event
        self.ts3conn = ts3conn

        self.channel_configs = []
        self.channel_configs = self.parse_channel_settings(CHANNEL_SETTINGS)
        if len(self.channel_configs) == 0:
            raise ValueError("This plugin requires at least one channel configuration")

        self.channel_minimums = self.get_channel_minimums()

        self.create_minimum_amount_of_channels()

        self.managed_channels = []
        self.managed_channels = self.find_channels_by_prefix()
        if len(self.managed_channels) == 0:
            ChannelManager.logger.info(
                "Seems like as you don't have any existing channels with the respective name patterns."
            )
        else:
            ChannelManager.logger.info(
                "Found the following existing channels, which I will manage: %s",
                str(self.managed_channels),
            )

        self.delete_channel_when_necessary()

    def get_channel_minimums(self):
        """
        Get current channel minimums.
        """
        channel_minimum = {}

        channel_configs = deepcopy(self.channel_configs)
        for channel_config in channel_configs:
            try:
                name_prefix = channel_config.pop("name_prefix")
                minimum = channel_config.pop("minimum", 1)
            except KeyError:
                ChannelManager.logger.exception(
                    "Could not retrieve the name prefix from the channel configuration."
                )
                continue

            channel_minimum[name_prefix] = int(minimum)

        return channel_minimum

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
                ChannelManager.logger.exception(
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

        channel_configs.append(deepcopy(channel_properties_dict))

        ChannelManager.logger.info(
            "Active channel configurations: %s", str(channel_configs)
        )

        return channel_configs

    def find_channels_by_prefix(self, channel_name_prefix=None):
        """
        Finds channels with a specific prefix.
        :param: channel_name_prefix: The prefix of the channel name, which you want to search for.
        :return: List of channels
        :type: list[dict]
        """
        try:
            all_channels = self.ts3conn.channellist()
        except TS3Exception:
            ChannelManager.logger.exception("Could not get the current channel list.")
            raise

        managed_channels_list = []

        if channel_name_prefix is not None:
            for channel in all_channels:
                if channel.get("channel_name").startswith(channel_name_prefix):
                    managed_channels_list.append(channel)

            return managed_channels_list

        channel_configs = deepcopy(self.channel_configs)
        for channel_config in channel_configs:
            try:
                name_prefix = channel_config.pop("name_prefix")
            except KeyError:
                ChannelManager.logger.exception(
                    "Could not retrieve the name prefix from the channel configuration."
                )
                continue

            for channel in all_channels:
                if channel.get("channel_name").startswith(name_prefix):
                    managed_channels_list.append(channel)

        return managed_channels_list

    def get_channel_id_by_name_pattern(self, channel_name_pattern):
        """
        Finds channels with a specific channel_name_pattern.
        :param channel_name: Channel name pattern
        :return: Channel ID
        :type: int
        """
        channel_id = None
        try:
            channel_id = int(
                self.ts3conn.channelfind(channel_name_pattern)[0].get("cid", "-1")
            )
        except TS3Exception:
            ChannelManager.logger.exception(
                "Error while finding a channel with the name pattern `%s`.",
                str(channel_name_pattern),
            )
            raise

        return channel_id

    def create_minimum_amount_of_channels(self):
        """
        Creates the minimum amount of configured channels.
        """
        channel_configs = deepcopy(self.channel_configs)
        for channel_config in channel_configs:
            ChannelManager.logger.debug(channel_config)

            try:
                parent_channel_name = channel_config.pop("parent_channel_name")
                name_prefix = channel_config.pop("name_prefix")
                # minium is not required here, but needs to be removed from the config list
                # to avoid an unknown parameter during channel creation.
                channel_config.pop("minimum")
            except KeyError:
                ChannelManager.logger.exception(
                    "Could not retrieve a required key from the channel configuration."
                )
                continue

            try:
                parent_channel_id = self.get_channel_id_by_name_pattern(
                    parent_channel_name
                )
            except TS3Exception:
                ChannelManager.logger.exception(
                    "Could not find any channel with the name pattern `%s`.",
                    str(parent_channel_name),
                )
                continue

            channel_minimum_available_count_diff = len(
                self.find_channels_by_prefix(name_prefix)
            ) - int(self.channel_minimums[name_prefix])

            amount_of_channels_to_create = 0
            if channel_minimum_available_count_diff < 0:
                ChannelManager.logger.info(
                    "Did not find any channel with the name prefix `%s`.",
                    str(name_prefix),
                )
                amount_of_channels_to_create = int(self.channel_minimums[name_prefix])

            if amount_of_channels_to_create == 0:
                ChannelManager.logger.info(
                    "All necessary `%s` channels exist. Nothing todo.", str(name_prefix)
                )
                continue

            channel_properties = []
            channel_properties.append(f"cpid={parent_channel_id}")
            channel_properties.append("channel_flag_semi_permanent=1")

            channel_permissions = []
            for key, value in channel_config.items():
                if key.startswith("channel_"):
                    channel_properties.append(f"{key}={value}")
                else:
                    channel_permissions.append({f"{key}": value})

            i = 1
            while i <= amount_of_channels_to_create:
                if i == 1:
                    channel_properties.append(f"channel_name={name_prefix} {i}")
                else:
                    channel_properties = [
                        channel_property.replace(
                            f"channel_name={name_prefix} {i-1}",
                            f"channel_name={name_prefix} {i}",
                        )
                        for channel_property in channel_properties
                    ]

                i += 1

                if DRY_RUN:
                    ChannelManager.logger.info(
                        "I would have created the following channel, when dry-run would be disabled: %s, %s",
                        str(channel_properties),
                        str(channel_permissions),
                    )
                else:
                    ChannelManager.logger.info(
                        "Creating the following channel: %s",
                        str(channel_properties),
                    )
                    try:
                        recently_created_channel = self.ts3conn._parse_resp_to_dict(
                            self.ts3conn._send("channelcreate", channel_properties)
                        )
                    except TS3QueryException as query_exception:
                        # channel name is already in use
                        if query_exception.id == 771:
                            ChannelManager.logger.debug(
                                "Channel already exists with this name: %s",
                                str(channel_properties),
                            )
                            continue

                        ChannelManager.logger.exception(
                            "Error while creating channel: %s", str(channel_properties)
                        )
                        raise

                    if len(channel_permissions) > 0:
                        ChannelManager.logger.info(
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
                                except TS3Exception:
                                    ChannelManager.logger.exception(
                                        "Failed to set the channel permission `%s` for the cid=%s.",
                                        str(permsid),
                                        int(recently_created_channel.get("cid")),
                                    )
                                    raise

    def create_channel_when_necessary(self):
        """
        Creates a new channel, when necessary.
        """
        self.managed_channels = self.find_channels_by_prefix()

        channel_stats = {}

        channel_configs = deepcopy(self.channel_configs)
        for channel_config in channel_configs:
            try:
                parent_channel_name = channel_config.pop("parent_channel_name")
                name_prefix = channel_config.pop("name_prefix")
                # minium is not required here, but needs to be removed from the config list
                # to avoid an unknown parameter during channel creation.
                channel_config.pop("minimum")
            except KeyError:
                ChannelManager.logger.exception(
                    "Could not retrieve the name prefix from the channel configuration."
                )
                continue

            channel_stats[name_prefix] = []

            for channel in self.managed_channels:
                if channel.get("channel_name").startswith(name_prefix):
                    channel_stats[name_prefix].append(channel)

        for channel_name_prefix, channels in channel_stats.items():
            ChannelManager.logger.debug(
                "Checking the existing channels for the channel configuration `%s`.",
                str(channel_name_prefix),
            )

            if any(int(channel["total_clients"]) == 0 for channel in channels):
                ChannelManager.logger.debug(
                    "There exists at least one channel with the prefix `%s`, which has zero clients in it. No further channels required.",
                    str(channel_name_prefix),
                )
                continue

            try:
                parent_channel_id = self.get_channel_id_by_name_pattern(
                    parent_channel_name
                )
            except TS3Exception:
                ChannelManager.logger.exception(
                    "Could not find any channel with the name pattern `%s`.",
                    str(parent_channel_name),
                )
                continue

            channel_properties = []
            channel_properties.append(f"cpid={parent_channel_id}")
            channel_properties.append("channel_flag_semi_permanent=1")

            existing_channel_numbers = []
            for channel in channels:
                existing_channel_numbers.append(
                    int(
                        channel["channel_name"].replace(channel_name_prefix, "").strip()
                    )
                )

            iterator_existing_channel_numbers = iter(existing_channel_numbers)

            channel_number = None
            last_channel_number = None
            i = 0
            while channel_number is None:
                i += 1

                try:
                    last_channel_number = next(iterator_existing_channel_numbers)
                except StopIteration:
                    previous_channel_number = last_channel_number
                    channel_number = last_channel_number + 1
                    break

                if int(i) != int(last_channel_number):
                    previous_channel_number = i - 1
                    channel_number = i

            channel_properties.append(
                f"channel_name={channel_name_prefix} {channel_number}"
            )

            for channel in channels:
                if (
                    channel["channel_name"]
                    == f"{channel_name_prefix} {previous_channel_number}"
                ):
                    previous_channel_id = channel["cid"]
                    break

            channel_properties.append(f"channel_order={previous_channel_id}")

            channel_permissions = []
            for key, value in channel_config.items():
                if key.startswith("channel_"):
                    channel_properties.append(f"{key}={value}")
                else:
                    channel_permissions.append({f"{key}": value})

            if DRY_RUN:
                ChannelManager.logger.info(
                    "I would have created the following channel, when dry-run would be disabled: %s, %s",
                    str(channel_properties),
                    str(channel_permissions),
                )
            else:
                ChannelManager.logger.info(
                    "Creating the following channel: %s",
                    str(channel_properties),
                )

                try:
                    recently_created_channel = self.ts3conn._parse_resp_to_dict(
                        self.ts3conn._send("channelcreate", channel_properties)
                    )
                except TS3Exception:
                    ChannelManager.logger.exception(
                        "Error while creating channel: %s", str(channel_properties)
                    )
                    raise

                if len(channel_permissions) > 0:
                    ChannelManager.logger.info(
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
                            except TS3Exception:
                                ChannelManager.logger.exception(
                                    "Failed to set the channel permission `%s` for the cid=%s.",
                                    str(permsid),
                                    int(recently_created_channel.get("cid")),
                                )
                                raise

    def get_channel_stats(self):
        """
        Get current channel statistics.
        """
        managed_channels = self.find_channels_by_prefix()

        channel_stats = {}

        channel_configs = deepcopy(self.channel_configs)
        for channel_config in channel_configs:
            try:
                name_prefix = channel_config.pop("name_prefix")
            except KeyError:
                ChannelManager.logger.exception(
                    "Could not retrieve the name prefix from the channel configuration."
                )
                continue

            channel_stats[name_prefix] = []

            for channel in managed_channels:
                if channel.get("channel_name").startswith(name_prefix):
                    channel_stats[name_prefix].append(channel)

        return channel_stats

    def delete_channel_when_necessary(self):
        """
        Deletes an existing channel, when necessary.
        """
        channel_stats = self.get_channel_stats()

        for channel_name_prefix, channels in channel_stats.items():
            ChannelManager.logger.debug(
                "Checking the existing channels for the channel configuration `%s`.",
                str(channel_name_prefix),
            )

            if len(channels) <= int(self.channel_minimums[channel_name_prefix]):
                ChannelManager.logger.debug(
                    "For the channel configuration `%s` exist only the minimum amount of channels. No further channels will be deleted.",
                    str(channel_name_prefix),
                )
                continue

            empty_channels = []
            for channel in channels:
                if int(channel["total_clients"]) == 0:
                    empty_channels.append(channel)

            if len(empty_channels) <= 1:
                ChannelManager.logger.debug(
                    "At least one empty channel must exist for `%s`, so no channel will be deleted.",
                    str(channel_name_prefix),
                )
                continue

            while len(empty_channels) > 1:
                channel_stats = self.get_channel_stats()

                if len(channel_stats[channel_name_prefix]) <= int(
                    self.channel_minimums[channel_name_prefix]
                ):
                    ChannelManager.logger.debug(
                        "For the channel configuration `%s` exist only the minimum amount of channels. No further channels will be deleted.",
                        str(channel_name_prefix),
                    )
                    break

                try:
                    channel_to_delete = empty_channels[len(empty_channels) - 1]
                    del empty_channels[len(empty_channels) - 1]
                except IndexError:
                    break

                if DRY_RUN:
                    ChannelManager.logger.info(
                        "I would have deleted the following channel, when dry-run would be disabled: %s",
                        str(channel_to_delete),
                    )
                else:
                    ChannelManager.logger.info(
                        "Deleting the following channel: %s",
                        str(channel_to_delete),
                    )

                    try:
                        self.ts3conn._send(
                            "channeldelete",
                            [f"cid={int(channel_to_delete.get('cid'))}"],
                        )
                    except TS3QueryException as query_exception:
                        # invalid channelID -> might be caused by a race-condition
                        if query_exception.id == 768:
                            continue

                        ChannelManager.logger.exception(
                            "Error while deleting channel: %s", str(channel_to_delete)
                        )
                        raise


@event(
    ClientEnteredEvent,
    ClientLeftEvent,
    ClientMovedEvent,
    ClientMovedSelfEvent,
    ClientKickedEvent,
    ClientBannedEvent,
)
def client_event(_event_data):
    """
    A client entered or left a channel, moved or were moved to a different channel or were kicked / banned from the channel / server.
    """
    if PLUGIN_INFO is not None:
        ChannelManager.create_channel_when_necessary(self=PLUGIN_INFO)
        ChannelManager.delete_channel_when_necessary(self=PLUGIN_INFO)


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
        ChannelManager.logger.exception(
            "Error while sending the plugin version as a message to the client!"
        )


@command(f"{PLUGIN_COMMAND_NAME} start")
def start_plugin(_sender=None, _msg=None):
    """
    Start the ChannelManager by clearing the PLUGIN_STOPPER signal and starting the mover.
    """
    global PLUGIN_INFO
    if PLUGIN_INFO is None:
        if DRY_RUN:
            ChannelManager.logger.info(
                "Dry run is enabled - logging actions intead of actually performing them."
            )

        PLUGIN_INFO = ChannelManager(PLUGIN_STOPPER, BOT.ts3conn)
        PLUGIN_STOPPER.clear()
        PLUGIN_INFO.start()


@command(f"{PLUGIN_COMMAND_NAME} stop")
def stop_plugin(_sender=None, _msg=None):
    """
    Stop the ChannelManager by setting the PLUGIN_STOPPER signal and undefining the mover.
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
    **channel_settings,
):
    """
    Sets up this plugin.
    """
    global BOT, AUTO_START, DRY_RUN, CHANNEL_SETTINGS

    BOT = ts3bot
    AUTO_START = auto_start
    DRY_RUN = enable_dry_run
    CHANNEL_SETTINGS = channel_settings

    if CHANNEL_SETTINGS is None:
        ChannelManager.logger.error(
            "Expected at least a configuration for one channel. Aborting as I have nothing todo."
        )
        return

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
