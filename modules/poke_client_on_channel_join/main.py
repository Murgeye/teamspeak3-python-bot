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

PLUGIN_VERSION = 0.1
PLUGIN_COMMAND_NAME = "pokeclientonchanneljoin"
PLUGIN_INFO: Union[None, "PokeClientOnChannelJoin"] = None
PLUGIN_STOPPER = threading.Event()
BOT: teamspeak_bot.Ts3Bot

# defaults for configureable options
AUTO_START = True
DRY_RUN = False  # log instead of performing actual actions
CHANNEL_SETTINGS = None


class PokeClientOnChannelJoin(Thread):
    """
    PokeClientOnChannelJoin class. Creates a channel, when a client requests one through a specific channel and grants the client a specific channel group.
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
        Create a new PokeClientOnChannelJoin object.
        :param stop_event: Event to signalize the PokeClientOnChannelJoin to stop moving.
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

    def get_channel_by_name(self, name="Support Lobby"):
        """
        Get the channel id of the channel specified by name.
        :param name: Channel name
        :return: Channel id
        """
        try:
            channel_id = self.ts3conn.channelfind(name)[0].get("cid", "-1")
        except TS3Exception:
            PokeClientOnChannelJoin.logger.exception(
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
                PokeClientOnChannelJoin.logger.exception(
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

            if channel_setting_name == "team_servergroups":
                for servergroup_name in value.split(","):
                    channel_properties_dict[
                        "team_client_database_ids"
                    ] = self.get_servergroup_client_database_ids(servergroup_name)

        channel_configs.append(deepcopy(channel_properties_dict))

        PokeClientOnChannelJoin.logger.info(
            "Active channel configurations: %s", str(channel_configs)
        )

        return channel_configs

    def get_servergroup_client_database_ids(self, servergroup_name):
        """
        Returns a list of client database ids of the specified servergroup.
        :param: servergroup_name: The name of a servergroup.
        :returns: List of clients, which are member of the servergroups.
        """
        servergroupclient_list = []

        try:
            servergroup_list = self.ts3conn._parse_resp_to_list_of_dicts(
                self.ts3conn._send(
                    "servergrouplist",
                )
            )
        except TS3QueryException:
            PokeClientOnChannelJoin.logger.exception(
                "Failed to get the servergroup list.",
            )
            raise

        servergroup_id = None
        for servergroup in servergroup_list:
            if str(servergroup.get("name")) != str(servergroup_name):
                continue

            servergroup_id = int(servergroup.get("sgid"))
            break

        if servergroup_id is None:
            PokeClientOnChannelJoin.logger.error(
                "Could not find any servergroup with the name '%s'.",
                str(servergroup_name),
            )
            return servergroupclient_list

        try:
            servergroupclient_list.append(
                self.ts3conn._parse_resp_to_list_of_dicts(
                    self.ts3conn._send(
                        "servergroupclientlist",
                        [f"sgid={int(servergroup_id)}"],
                    )
                )
            )
        except TS3QueryException:
            PokeClientOnChannelJoin.logger.exception(
                "Failed to get the client list of the servergroup sgid=%s.",
                int(servergroup_id),
            )
            raise

        client_database_ids = []
        for client_list in servergroupclient_list:
            for client in client_list:
                client_database_ids.append(client.get("cldbid"))

        return client_database_ids

    def poke_client(self, client_id, client_info, poke_message):
        """
        Pokes clients with the configured message.
        :param: client_id: The client ID of a client, which should get poked.
        :param: client_info: The client info of a client, which should get poked.
        :param: poke_message: The message, which should be sent as poke.
        """
        if DRY_RUN:
            PokeClientOnChannelJoin.logger.info(
                "If dry-run would be disabled, I would have poked the following client: client_database_id=%s, client_nickname=%s, poke_message=%s",
                int(client_info.get("client_database_id")),
                str(client_info.get("client_nickname")),
                str(poke_message),
            )
        else:
            PokeClientOnChannelJoin.logger.debug(
                "Poking the following client: client_database_id=%s, client_nickname=%s, poke_message=%s",
                int(client_info.get("client_database_id")),
                str(client_info.get("client_nickname")),
                str(poke_message),
            )

            try:
                self.ts3conn.clientpoke(int(client_id), str(poke_message))
            except TS3QueryException:
                PokeClientOnChannelJoin.logger.exception(
                    "Failed to poke the client_database_id=%s, client_nickname=%s with the message '%s'.",
                    int(client_info.get("client_database_id")),
                    str(client_info.get("client_nickname")),
                    str(poke_message),
                )
                raise

    def poke_servergroup_clients(self, channel_config, client_info):
        """
        Pokes clients, which are online and member of the specified servergroups with the configured message.
        :param: channel_config: The channel configuration, which needs to be checked for poking clients.
        :param: client_info: The client info of the client, which joined the channel.
        """
        try:
            team_poke_message = channel_config["team_poke_message"]
        except KeyError:
            PokeClientOnChannelJoin.logger.debug(
                "No team poke message has been defined in the config. Nothing todo!"
            )
            return

        try:
            client_list = self.ts3conn.clientlist()
        except TS3Exception:
            PokeClientOnChannelJoin.logger.exception(
                "Failed to get the list of currently connected clients.",
            )
            raise

        servergroup_client_ids_to_poke = []
        for connected_client in client_list:
            if (
                connected_client.get("client_database_id")
                not in channel_config["team_client_database_ids"]
            ):
                PokeClientOnChannelJoin.logger.debug(
                    "The following client is not member of any servergroup: %s",
                    str(connected_client),
                )
                continue

            servergroup_client_ids_to_poke.append(int(connected_client.get("clid")))

        if re.search("%c", team_poke_message):
            team_poke_message = team_poke_message.replace(
                "%c", str(client_info.get("client_nickname"))
            )

        for servergroup_client_id in servergroup_client_ids_to_poke:
            if re.search("%u", team_poke_message):
                try:
                    client_info = self.ts3conn.clientinfo(int(servergroup_client_id))
                except TS3Exception:
                    PokeClientOnChannelJoin.logger.exception(
                        "Failed to get the client info of clid=%s.",
                        int(servergroup_client_id),
                    )
                    raise

                servergroup_team_poke_message = team_poke_message.replace(
                    "%u", str(client_info.get("client_nickname"))
                )
            else:
                servergroup_team_poke_message = team_poke_message

            self.poke_client(
                client_id=servergroup_client_id,
                client_info=client_info,
                poke_message=servergroup_team_poke_message,
            )

    def poke_user(self, channel_config, client_id, client_info):
        """
        Pokes the client, which joined a respective channel with the configured message.
        :param: channel_config: The channel configuration, which needs to be checked for poking clients.
        :param: client_id: The client ID of the client, which joined the channel.
        :param: client_info: The client info of the client, which joined the channel.
        """
        try:
            user_poke_message = channel_config["user_poke_message"]
        except KeyError:
            PokeClientOnChannelJoin.logger.debug(
                "No user poke message has been defined in the config. Nothing todo!"
            )
            return

        if re.search("%u", user_poke_message):
            user_poke_message = user_poke_message.replace(
                "%u", str(client_info.get("client_nickname"))
            )

        self.poke_client(
            client_id=client_id, client_info=client_info, poke_message=user_poke_message
        )

    def run(self, client=None):
        """
        Checks the event and pokes client, when necessary.
        :param: client: The event data of the client, which joined a channel.
        """
        if client is None:
            PokeClientOnChannelJoin.logger.debug(
                "No client has been provided. Nothing todo!"
            )
            return

        PokeClientOnChannelJoin.logger.debug(
            "Received an event for this client: %s", str(client)
        )

        channel_config = None
        for config in self.channel_configs:
            if int(config["channel_id"]) == int(client.target_channel_id):
                channel_config = config
                break

        if channel_config is None:
            PokeClientOnChannelJoin.logger.debug(
                "The client did not join any channel, which should poke clients."
            )
            return

        if not any(
            key in channel_config for key in ("team_poke_message", "user_poke_message")
        ):
            raise ValueError(
                f"The channel config `{str(channel_config['channel_name'])}` is invalid. At least one of these arguments must be defined: team_poke_message, user_poke_message"
            )

        try:
            client_info = self.ts3conn.clientinfo(client.clid)
        except AttributeError:
            PokeClientOnChannelJoin.logger.exception(
                "The client has no clid: %s.", str(client)
            )
            raise
        except TS3Exception:
            PokeClientOnChannelJoin.logger.exception(
                "Failed to get the client info of clid=%s.", int(client.clid)
            )
            raise

        self.poke_servergroup_clients(
            channel_config=channel_config, client_info=client_info
        )

        self.poke_user(
            channel_config=channel_config,
            client_id=client.clid,
            client_info=client_info,
        )


@event(ClientEnteredEvent, ClientMovedEvent, ClientMovedSelfEvent)
def client_joined(event_data):
    """
    Client joined the server or a channel or somebody moved the client into a different channel.
    """
    if PLUGIN_INFO is not None:
        PokeClientOnChannelJoin.run(self=PLUGIN_INFO, client=event_data)


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
        PokeClientOnChannelJoin.logger.exception(
            "Error while sending the plugin version as a message to the client!"
        )


@command(f"{PLUGIN_COMMAND_NAME} start")
def start_plugin(_sender=None, _msg=None):
    """
    Start the PokeClientOnChannelJoin by clearing the PLUGIN_STOPPER signal and starting the mover.
    """
    global PLUGIN_INFO
    if PLUGIN_INFO is None:
        if DRY_RUN:
            PokeClientOnChannelJoin.logger.info(
                "Dry run is enabled - logging actions intead of actually performing them."
            )

        PLUGIN_INFO = PokeClientOnChannelJoin(PLUGIN_STOPPER, BOT.ts3conn)
        PLUGIN_STOPPER.clear()
        PLUGIN_INFO.start()


@command(f"{PLUGIN_COMMAND_NAME} stop")
def stop_plugin(_sender=None, _msg=None):
    """
    Stop the PokeClientOnChannelJoin by setting the PLUGIN_STOPPER signal and undefining the mover.
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
