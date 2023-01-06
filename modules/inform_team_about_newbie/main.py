# standard imports
import logging
import threading
from threading import Thread
from typing import Union

# third-party imports
from ts3API.Events import ClientEnteredEvent
from ts3API.TS3Connection import TS3QueryException
from ts3API.utilities import TS3Exception

# local imports
from module_loader import setup_plugin, exit_plugin, command, event
import teamspeak_bot

PLUGIN_VERSION = 0.1
PLUGIN_COMMAND_NAME = "informteamaboutnewbie"
PLUGIN_INFO: Union[None, "InformTeamAboutNewbie"] = None
PLUGIN_STOPPER = threading.Event()
BOT: teamspeak_bot.Ts3Bot

# defaults for configureable options
AUTO_START = True
DRY_RUN = False  # log instead of performing actual actions
NEWBIE_SERVERGROUP_NAME = "Guest"
SUPPORT_CHANNEL_NAME = None
TEAM_SERVERGROUP_NAMES = "Moderator"
NEWBIE_POKE_MESSAGE = "A team member will welcome you in a moment."
TEAM_POKE_MESSAGE = "A newbie joined!"


class InformTeamAboutNewbie(Thread):
    """
    InformTeamAboutNewbie class. Pokes team members, when a new client joined the server.
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
        Create a new InformTeamAboutNewbie object.
        :param stop_event: Event to signalize the InformTeamAboutNewbie to stop moving.
        :type stop_event: threading.Event
        :param ts3conn: Connection to use
        :type: TS3Connection
        """
        Thread.__init__(self)
        self.stopped = stop_event
        self.ts3conn = ts3conn

        self.newbie_servergroup = None
        self.newbie_servergroup = self.get_servergroup_by_name(NEWBIE_SERVERGROUP_NAME)
        if self.newbie_servergroup is None:
            InformTeamAboutNewbie.logger.error(
                "Could not find any servergroup with the following name: %s",
                str(NEWBIE_SERVERGROUP_NAME),
            )

        self.support_channel = None
        if SUPPORT_CHANNEL_NAME is not None:
            self.support_channel = self.get_channel_by_name(SUPPORT_CHANNEL_NAME)
            if self.support_channel is None:
                InformTeamAboutNewbie.logger.error(
                    "Could not find any channel with the following name: %s",
                    str(SUPPORT_CHANNEL_NAME),
                )

        self.team_servergroups = []
        for team_servergroup_name in TEAM_SERVERGROUP_NAMES.split(","):
            servergroup = self.get_servergroup_by_name(team_servergroup_name)
            if servergroup is not None:
                self.team_servergroups.append(servergroup)

        if len(self.team_servergroups) == 0:
            InformTeamAboutNewbie.logger.error(
                "Could not find any team servergroup with the following names: %s",
                str(TEAM_SERVERGROUP_NAMES),
            )
        else:
            InformTeamAboutNewbie.logger.info(
                "Found the following team servergroups: %s",
                str(self.team_servergroups),
            )

        self.newbie_poke_message = NEWBIE_POKE_MESSAGE
        self.team_poke_message = TEAM_POKE_MESSAGE

    def get_servergroup_by_name(self, name="Guest"):
        """
        Get the servergroup specified by name.
        :param name: Servergroup name
        :return: Servergroup
        """
        servergroup = None
        try:
            servergroup = self.ts3conn.find_servergroup_by_name(str(name))
        except TS3Exception:
            InformTeamAboutNewbie.logger.exception(
                "Could not find any servergroup with the following name: %s", str(name)
            )
            raise

        return servergroup

    def get_channel_by_name(self, name="Support"):
        """
        Get the channel specified by name.
        :param name: Channel name
        :return: Channel information
        """
        try:
            channel = self.ts3conn.channelfind(name)[0]
        except TS3Exception:
            InformTeamAboutNewbie.logger.exception(
                "Error while finding a channel with the name `%s`.", str(name)
            )
            raise

        return channel

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
            InformTeamAboutNewbie.logger.exception(
                "Failed to get the list of assigned servergroups for the client cldbid=%s.",
                int(cldbid),
            )
            return client_servergroup_ids

        for servergroup in client_servergroups:
            client_servergroup_ids.append(servergroup.get("sgid"))

        InformTeamAboutNewbie.logger.debug(
            "client_database_id=%s has these servergroups: %s",
            int(cldbid),
            str(client_servergroup_ids),
        )

        return client_servergroup_ids

    def move_newbie_to_support(self, client_id):
        """
        Moves the newbie client to the support channel.
        """
        if DRY_RUN:
            InformTeamAboutNewbie.logger.info(
                "If dry-run would be disabled, I would have moved the following client to the supporter channel: clid=%s",
                int(client_id),
            )
        else:
            InformTeamAboutNewbie.logger.debug(
                "Moving the following client to the supporter channel: clid=%s",
                int(client_id),
            )

            try:
                self.ts3conn.clientmove(self.support_channel.get("cid"), client_id)
            except TS3QueryException:
                InformTeamAboutNewbie.logger.exception(
                    "Failed to move the clid=%s to the supporter channel.",
                    int(client_id),
                )
                raise

    def get_team_member_list(self):
        """
        Returns a list of team member of the specified team servergroups.
        :returns: List of clients, which are member of the servergroups.
        """
        servergroupclient_list = []

        for servergroup in self.team_servergroups:
            try:
                servergroupclient_list.append(
                    self.ts3conn._parse_resp_to_list_of_dicts(
                        self.ts3conn._send(
                            "servergroupclientlist",
                            [f"sgid={int(servergroup.get('sgid'))}"],
                        )
                    )
                )
            except TS3QueryException:
                InformTeamAboutNewbie.logger.exception(
                    "Failed to get the client list of the servergroup sgid=%s.",
                    int(servergroup.get("sgid")),
                )
                raise

        client_database_ids = []
        for client_list in servergroupclient_list:
            for client in client_list:
                client_database_ids.append(client.get("cldbid"))

        return client_database_ids

    def poke_team(self):
        """
        Pokes the team, when a newbie joined the server.
        """
        try:
            client_list = self.ts3conn.clientlist()
        except TS3QueryException:
            InformTeamAboutNewbie.logger.exception(
                "Failed to get a current list of connected clients."
            )
            raise

        team_member_database_id_list = self.get_team_member_list()

        team_member_client_ids = []
        for client in client_list:
            if client.get("client_database_id") not in team_member_database_id_list:
                InformTeamAboutNewbie.logger.debug(
                    "The following client is not member of any team servergroup: %s",
                    str(client),
                )
                continue

            team_member_client_ids.append(client.get("clid"))

        for client_id in team_member_client_ids:
            if DRY_RUN:
                InformTeamAboutNewbie.logger.info(
                    "If dry-run would be disabled, I would have poked the following client about a newbie: clid=%s",
                    int(client_id),
                )
            else:
                InformTeamAboutNewbie.logger.debug(
                    "Poking the following client about a newbie: clid=%s",
                    int(client_id),
                )

                try:
                    self.ts3conn.clientpoke(client_id, str(self.team_poke_message))
                except TS3QueryException:
                    InformTeamAboutNewbie.logger.exception(
                        "Failed to poke the clid=%s.", int(client_id)
                    )
                    raise

    def poke_newbie(self, client_id):
        """
        Pokes the newbie, that the team is informed.
        :params: client_id: The client ID of the newbie.
        """
        if DRY_RUN:
            InformTeamAboutNewbie.logger.info(
                "If dry-run would be disabled, I would have poked the following newbie, that the team is informed: clid=%s",
                int(client_id),
            )
        else:
            InformTeamAboutNewbie.logger.debug(
                "Poking the following newbie, that the team is informed: clid=%s",
                int(client_id),
            )

            try:
                self.ts3conn.clientpoke(client_id, str(self.newbie_poke_message))
            except TS3QueryException:
                InformTeamAboutNewbie.logger.exception(
                    "Failed to poke the clid=%s.", int(client_id)
                )
                raise

    def check_joined_client(self, client=None):
        """
        Checks if the joined client is a newbie or not and follows up with the necessary steps.
        :params: client: The `ClientEnteredEvent` event data for the joined client.
        """
        if client is None:
            InformTeamAboutNewbie.logger.debug(
                "No client has been provided. Nothing todo!"
            )
            return

        client_servergroup_ids = self.get_servergroups_by_client(client.client_dbid)

        if self.newbie_servergroup.get("sgid") not in client_servergroup_ids:
            InformTeamAboutNewbie.logger.debug(
                "The client client_database_id=%s is not member of the sgid=%s (%s)",
                int(client.client_dbid),
                int(self.newbie_servergroup.get("sgid")),
                str(self.newbie_servergroup.get("name")),
            )
            return

        InformTeamAboutNewbie.logger.info(
            "The following newbie joined the server: client_database_id=%s, client_uid=%s, client_name=%s",
            int(client.client_dbid),
            str(client.client_uid),
            str(client.client_name),
        )

        if self.support_channel is not None:
            self.move_newbie_to_support(client.client_id)

        self.poke_team()

        self.poke_newbie(client.client_id)


@event(ClientEnteredEvent)
def client_joined(event_data):
    """
    Client joined the server or a channel or somebody moved the client into a different channel.
    """
    if PLUGIN_INFO is not None:
        InformTeamAboutNewbie.check_joined_client(self=PLUGIN_INFO, client=event_data)


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
        InformTeamAboutNewbie.logger.exception(
            "Error while sending the plugin version as a message to the client!"
        )


@command(f"{PLUGIN_COMMAND_NAME} start")
def start_plugin(_sender=None, _msg=None):
    """
    Start the InformTeamAboutNewbie by clearing the PLUGIN_STOPPER signal and starting the mover.
    """
    global PLUGIN_INFO
    if PLUGIN_INFO is None:
        if DRY_RUN:
            InformTeamAboutNewbie.logger.info(
                "Dry run is enabled - logging actions intead of actually performing them."
            )

        PLUGIN_INFO = InformTeamAboutNewbie(PLUGIN_STOPPER, BOT.ts3conn)
        PLUGIN_STOPPER.clear()
        PLUGIN_INFO.start()


@command(f"{PLUGIN_COMMAND_NAME} stop")
def stop_plugin(_sender=None, _msg=None):
    """
    Stop the InformTeamAboutNewbie by setting the PLUGIN_STOPPER signal and undefining the mover.
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
    newbie_servergroup_name=NEWBIE_SERVERGROUP_NAME,
    support_channel_name=SUPPORT_CHANNEL_NAME,
    team_servergroup_names=TEAM_SERVERGROUP_NAMES,
    newbie_poke_message=NEWBIE_POKE_MESSAGE,
    team_poke_message=TEAM_POKE_MESSAGE,
):
    """
    Sets up this plugin.
    """
    global BOT, AUTO_START, DRY_RUN, NEWBIE_SERVERGROUP_NAME, SUPPORT_CHANNEL_NAME, TEAM_SERVERGROUP_NAMES, NEWBIE_POKE_MESSAGE, TEAM_POKE_MESSAGE

    BOT = ts3bot
    AUTO_START = auto_start
    DRY_RUN = enable_dry_run
    NEWBIE_SERVERGROUP_NAME = newbie_servergroup_name
    SUPPORT_CHANNEL_NAME = support_channel_name
    TEAM_SERVERGROUP_NAMES = team_servergroup_names

    if len(newbie_poke_message) > 100:
        InformTeamAboutNewbie.logger.error(
            "The defined poke message has a length of %s characters, but only 100 are technically possible.",
            len(newbie_poke_message),
        )
        raise ValueError

    NEWBIE_POKE_MESSAGE = newbie_poke_message

    if len(team_poke_message) > 100:
        InformTeamAboutNewbie.logger.error(
            "The defined poke message has a length of %s characters, but only 100 are technically possible.",
            len(team_poke_message),
        )
        raise ValueError

    TEAM_POKE_MESSAGE = team_poke_message

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
