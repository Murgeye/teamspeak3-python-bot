# standard imports
import logging
import threading
import traceback
from threading import Thread
from typing import Union
import sys

import re

# third-party imports
from ts3API.TS3Connection import TS3QueryException
from ts3API.utilities import TS3Exception

# local imports
from module_loader import setup_plugin, exit_plugin, command
import teamspeak_bot

PLUGIN_VERSION = 0.1
PLUGIN_COMMAND_NAME = "badnickname"
PLUGIN_INFO: Union[None, "BadNickname"] = None
PLUGIN_STOPPER = threading.Event()
BOT: teamspeak_bot.Ts3Bot

# defaults for configureable options
AUTO_START = True
DRY_RUN = False  # log instead of performing actual actions
CHECK_FREQUENCY_SECONDS = 60.0 * 5  # 300 seconds => 5 minutes
SERVERGROUPS_TO_EXCLUDE = None
BAD_NAME_PATTERN = "[a|4]dm[i|1]n"
KICK_REASON_MESSAGE = "Your client nickname is not allowed!"


class BadNickname(Thread):
    """
    BadNickname class. Kicks clients from the server which are using a not allowed nickname.
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
        Create a new BadNickname object.
        :param stop_event: Event to signalize the BadNickname to stop.
        :type stop_event: threading.Event
        :param ts3conn: Connection to use
        :type: TS3Connection
        """
        Thread.__init__(self)
        self.stopped = stop_event
        self.ts3conn = ts3conn
        self.update_servergroup_ids_list()
        self.client_list = None
        self.bad_nickname_client_list = None
        self.regex_object = self.compile_regex_pattern(BAD_NAME_PATTERN)

        if self.regex_object is None:
            self.logger.error(
                "Could not compile your given regex: `%s`.", str(BAD_NAME_PATTERN)
            )

    def run(self):
        """
        Thread run method. Starts the plugin.
        """
        self.logger.info("Thread started")
        try:
            self.loop_until_stopped()
        except BaseException:
            self.logger.exception("Exception occured in run:")

    def compile_regex_pattern(self, regex_pattern):
        """
        Compiles and thus tests the given regex pattern.
        :param regex_pattern: A regex pattern string
        :return: Regular expression object
        """
        regex_object = None
        try:
            regex_object = re.compile(regex_pattern)
        except re.error as query_exception:
            self.logger.error(
                "The provided regex pattern is invalid: %s", str(regex_pattern)
            )
            self.logger.exception(query_exception.msg)

        return regex_object

    def update_client_list(self):
        """
        Update list of clients with idle time.
        :return: List of connected clients with their idle time.
        """
        try:
            self.client_list = []
            for client in self.ts3conn.clientlist():
                if int(client.get("client_type")) == 1:
                    self.logger.debug(
                        "update_client_list ignoring ServerQuery client: %s",
                        str(client),
                    )
                    continue

                self.client_list.append(client)

            self.logger.debug("update_client_list: %s", str(self.client_list))
        except TS3Exception:
            self.logger.exception("Error getting client list!")
            self.client_list = []

    def update_servergroup_ids_list(self):
        """
        Updates the list of servergroup IDs, which should be ignored.
        """
        self.servergroup_ids_to_ignore = []

        if SERVERGROUPS_TO_EXCLUDE is None:
            self.logger.debug("No servergroups to exclude defined. Nothing todo.")
            return

        try:
            servergroup_list = self.ts3conn.servergrouplist()
        except TS3QueryException:
            self.logger.exception("Failed to get the list of available servergroups.")

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
            self.logger.exception(
                "Failed to get the list of assigned servergroups for the client cldbid=%s.",
                int(cldbid),
            )
            return client_servergroup_ids

        for servergroup in client_servergroups:
            client_servergroup_ids.append(servergroup.get("sgid"))

        self.logger.debug(
            "client_database_id=%s has these servergroups: %s",
            int(cldbid),
            str(client_servergroup_ids),
        )

        return client_servergroup_ids

    def get_client_list_with_bad_nickname(self):
        """
        Get list of clients which have a bad nickname.
        :return: List of clients which have a bad nickname.
        """
        if self.client_list is None:
            self.logger.debug("get_client_list_with_bad_nickname client_list is None!")
            return []

        self.logger.debug(
            "get_client_list_with_bad_nickname current client_list: %s!",
            str(self.client_list),
        )

        if self.regex_object is None:
            self.logger.error("get_client_list_with_bad_nickname regex is invalid!")
            return []

        client_bad_nickname_list = []
        for client in self.client_list:
            self.logger.debug(
                "get_client_list_with_bad_nickname checking client: %s", str(client)
            )

            if "cid" not in client.keys():
                self.logger.error(
                    "get_client_list_with_bad_nickname client without cid: %s!",
                    str(client),
                )
                continue

            if "client_nickname" not in client.keys():
                self.logger.error(
                    "get_client_list_with_bad_nickname client without client_nickname: %s!",
                    str(client),
                )
                continue

            if client.get("client_type") == "1":
                self.logger.debug("Ignoring ServerQuery client: %s", str(client))
                continue

            if SERVERGROUPS_TO_EXCLUDE is not None:
                client_is_in_group = False
                for client_servergroup_id in self.get_servergroups_by_client(
                    client.get("client_database_id")
                ):
                    if client_servergroup_id in self.servergroup_ids_to_ignore:
                        self.logger.debug(
                            "The client is in the servergroup sgid=%s, which should be ignored: %s",
                            int(client_servergroup_id),
                            str(client),
                        )
                        client_is_in_group = True
                        break

                if client_is_in_group:
                    continue

            if not self.regex_object.search(client.get("client_nickname").casefold()):
                self.logger.debug(
                    "get_client_list_with_bad_nickname client has no bad nickname: %s!",
                    str(client),
                )
                continue

            self.logger.debug(
                "get_client_list_with_bad_nickname adding client to list: %s!",
                str(client),
            )
            client_bad_nickname_list.append(client)

        self.logger.debug(
            "get_client_list_with_bad_nickname updated client_list: %s!",
            str(client_bad_nickname_list),
        )

        return client_bad_nickname_list

    def kick_all_clients_with_bad_nickname(self):
        """
        Kick all clients with a bad nickname.
        """
        bad_nickname_list = self.get_client_list_with_bad_nickname()
        if bad_nickname_list is None:
            self.logger.debug("bad_nickname_list is empty. Nothing todo.")
            return

        for client in bad_nickname_list:
            self.logger.info(
                "Kicking %s clients from the server!", int(len(bad_nickname_list))
            )

            if DRY_RUN:
                self.logger.info(
                    "I would have kicked the following client from the server, when the dry-run would be disabled: %s",
                    str(client),
                )
            else:
                self.logger.info(
                    "Kicking the following client from the server: %s", str(client)
                )

                try:
                    self.ts3conn.clientkick(
                        int(client.get("clid", "-1")), 5, KICK_REASON_MESSAGE
                    )
                except TS3Exception:
                    self.logger.exception(
                        "Error kicking client clid=%s!", int(client.get("clid", "-1"))
                    )

    def loop_until_stopped(self):
        """
        Loop move functions until the stop signal is sent.
        """
        while not self.stopped.wait(float(CHECK_FREQUENCY_SECONDS)):
            self.logger.debug("Thread running!")

            try:
                self.update_client_list()
                self.kick_all_clients_with_bad_nickname()
            except BaseException:
                self.logger.error("Uncaught exception: %s", str(sys.exc_info()[0]))
                self.logger.error(str(sys.exc_info()[1]))
                self.logger.error(traceback.format_exc())

        self.logger.warning("Thread stopped!")


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
        BadNickname.logger.exception(
            "Error while sending the plugin version as a message to the client!"
        )


@command(f"{PLUGIN_COMMAND_NAME} start")
def start_plugin(_sender=None, _msg=None):
    """
    Start the BadNickname by clearing the PLUGIN_STOPPER signal and starting the plugin.
    """
    global PLUGIN_INFO
    if PLUGIN_INFO is None:
        if len(KICK_REASON_MESSAGE) > 40:
            BadNickname.logger.error(
                "The `kick_message` has %s characters, but only 40 are supported! Aborted the plugin start.",
                int(len(KICK_REASON_MESSAGE)),
            )
            return

        if DRY_RUN:
            BadNickname.logger.info(
                "Dry run is enabled - logging actions intead of actually performing them."
            )

        PLUGIN_INFO = BadNickname(PLUGIN_STOPPER, BOT.ts3conn)
        PLUGIN_STOPPER.clear()
        PLUGIN_INFO.start()


@command(f"{PLUGIN_COMMAND_NAME} stop")
def stop_plugin(_sender=None, _msg=None):
    """
    Stop the BadNickname by setting the PLUGIN_STOPPER signal and undefining the plugin.
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
    frequency=CHECK_FREQUENCY_SECONDS,
    exclude_servergroups=SERVERGROUPS_TO_EXCLUDE,
    name_pattern=BAD_NAME_PATTERN,
    kick_message=KICK_REASON_MESSAGE,
):
    """
    Sets up this plugin.
    """
    global BOT, AUTO_START, DRY_RUN, CHECK_FREQUENCY_SECONDS, SERVERGROUPS_TO_EXCLUDE, BAD_NAME_PATTERN, KICK_REASON_MESSAGE

    BOT = ts3bot
    AUTO_START = auto_start
    DRY_RUN = enable_dry_run
    CHECK_FREQUENCY_SECONDS = frequency
    SERVERGROUPS_TO_EXCLUDE = exclude_servergroups
    BAD_NAME_PATTERN = name_pattern
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
