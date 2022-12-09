import threading
import traceback
from threading import Thread

import ts3API.Events as Events
from ts3API.TS3Connection import TS3QueryException
from ts3API.utilities import TS3Exception

from Moduleloader import *
import Bot
from typing import Union

import re

plugin_version = 0.1
plugin_command_name = "badnickname"
plugin_info: Union[None, 'BadNickname'] = None
plugin_stopper = threading.Event()
bot: Bot.Ts3Bot

# defaults for configureable options
autoStart = True
dry_run = False # log instead of performing actual actions
check_frequency = 60.0 * 5 # 300 seconds => 5 minutes
servergroups_to_exclude = None
bad_name_pattern = "[a|4]dm[i|1]n"
kick_reason_message = "Your client nickname is not allowed!"

class BadNickname(Thread):
    """
    BadNickname class. Kicks clients from the server which are using a not allowed nickname.
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
    logger.info(f"Configured {class_name} logger")
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
        self.regex_object = self.compile_regex_pattern(bad_name_pattern)

        if self.regex_object is None:
            BadNickname.logger.error(f"Could not compile your given regex: `{bad_name_pattern}`.")

    def run(self):
        """
        Thread run method. Starts the plugin.
        """
        BadNickname.logger.info("Thread started")
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
        except re.error as e:
            logger.error(f"The provided regex pattern is invalid: {regex_pattern}")
            logger.exception(e.msg)

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
                    BadNickname.logger.debug(f"update_client_list ignoring ServerQuery client: {str(client)}")
                    continue

                self.client_list.append(client)

            BadNickname.logger.debug(f"update_client_list: {str(self.client_list)}")
        except TS3Exception:
            BadNickname.logger.exception("Error getting client list!")
            self.client_list = list()


    def update_servergroup_ids_list(self):
        """
        Updates the list of servergroup IDs, which should be ignored.
        """
        self.servergroup_ids_to_ignore = []

        if servergroups_to_exclude is None:
            BadNickname.logger.debug("No servergroups to exclude defined. Nothing todo.")
            return

        try:
            servergroup_list = self.ts3conn.servergrouplist()
        except TS3QueryException:
            BadNickname.logger.exception("Failed to get the list of available servergroups.")

        self.servergroup_ids_to_ignore.clear()
        for servergroup in servergroup_list:
            if servergroup.get("name") in servergroups_to_exclude.split(','):
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
            BadNickname.logger.exception(f"Failed to get the list of assigned servergroups for the client cldbid={cldbid}.")
            return client_servergroup_ids

        for servergroup in client_servergroups:
            client_servergroup_ids.append(servergroup.get("sgid"))

        BadNickname.logger.debug(f"client_database_id={cldbid} has these servergroups: {str(client_servergroup_ids)}")

        return client_servergroup_ids


    def get_client_list_with_bad_nickname(self):
        """
        Get list of clients which have a bad nickname.
        :return: List of clients which have a bad nickname.
        """
        if self.client_list is None:
            BadNickname.logger.debug("get_client_list_with_bad_nickname client_list is None!")
            return list()

        BadNickname.logger.debug(f"get_client_list_with_bad_nickname current client_list: {str(self.client_list)}!")

        if self.regex_object is None:
            BadNickname.logger.error("get_client_list_with_bad_nickname regex is invalid!")
            return list()

        client_bad_nickname_list = list()
        for client in self.client_list:
            BadNickname.logger.debug(f"get_client_list_with_bad_nickname checking client: {str(client)}")

            if "cid" not in client.keys():
                BadNickname.logger.error(f"get_client_list_with_bad_nickname client without cid: {str(client)}!")
                continue

            if "client_nickname" not in client.keys():
                BadNickname.logger.error(f"get_client_list_with_bad_nickname client without client_nickname: {str(client)}!")
                continue

            if client.get("client_type") == '1':
                BadNickname.logger.debug(f"Ignoring ServerQuery client: {client}")
                continue

            if servergroups_to_exclude is not None:
                client_is_in_group = False
                for client_servergroup_id in self.get_servergroups_by_client(client.get("client_database_id")):
                    if client_servergroup_id in self.servergroup_ids_to_ignore:
                        BadNickname.logger.debug(f"The client is in the servergroup sgid={client_servergroup_id}, which should be ignored: {client}")
                        client_is_in_group = True
                        break

                if client_is_in_group:
                    continue

            if not self.regex_object.search(client.get("client_nickname").casefold()):
                BadNickname.logger.debug(f"get_client_list_with_bad_nickname client has no bad nickname: {str(client)}!")
                continue

            BadNickname.logger.debug(f"get_client_list_with_bad_nickname adding client to list: {str(client)}!")
            client_bad_nickname_list.append(client)

        BadNickname.logger.debug(f"get_client_list_with_bad_nickname updated client_list: {str(client_bad_nickname_list)}!")

        return client_bad_nickname_list

    def kick_all_clients_with_bad_nickname(self):
        """
        Kick all clients with a bad nickname.
        """
        bad_nickname_list = self.get_client_list_with_bad_nickname()
        if bad_nickname_list is None:
            BadNickname.logger.debug("bad_nickname_list is empty. Nothing todo.")
            return

        BadNickname.logger.info(f"Kicking {len(bad_nickname_list)} clients from the server!")

        for client in bad_nickname_list:
            if dry_run:
                BadNickname.logger.info(f"I would have kicked the following client from the server, when the dry-run would be disabled: {str(client)}")
            else:
                BadNickname.logger.info(f"Kicking the following client from the server: {str(client)}")

                try:
                    self.ts3conn.clientkick(int(client.get("clid", '-1')), 5, kick_reason_message)
                except TS3Exception:
                    BadNickname.logger.exception(f"Error kicking client clid={str(client.get('clid', '-1'))}!")

    def loop_until_stopped(self):
        """
        Loop move functions until the stop signal is sent.
        """
        while not self.stopped.wait(float(check_frequency)):
            BadNickname.logger.debug("Thread running!")

            try:
                self.update_client_list()
                self.kick_all_clients_with_bad_nickname()
            except BaseException:
                BadNickname.logger.error("Uncaught exception:" + str(sys.exc_info()[0]))
                BadNickname.logger.error(str(sys.exc_info()[1]))
                BadNickname.logger.error(traceback.format_exc())

        BadNickname.logger.warning("Thread stopped!")
        self.client_channels = {}


@command(f"{plugin_command_name} version")
def send_version(sender=None, _msg=None):
    """
    Sends the plugin version as textmessage to the `sender`.
    """
    try:
        Bot.send_msg_to_client(bot.ts3conn, sender, f"This plugin is installed in the version `{str(plugin_version)}`.")
    except TS3Exception:
        BadNickname.logger.exception("Error while sending the plugin version as a message to the client!")


@command(f"{plugin_command_name} start")
def start_plugin(_sender=None, _msg=None):
    """
    Start the BadNickname by clearing the plugin_stopper signal and starting the plugin.
    """
    global plugin_info
    if plugin_info is None:
        if len(kick_reason_message) > 40:
            BadNickname.logger.error(f"The `kick_message` has {len(kick_reason_message)} characters, but only 40 are supported! Aborted the plugin start.")
            return

        if dry_run:
            BadNickname.logger.info("Dry run is enabled - logging actions intead of actually performing them.")

        plugin_info = BadNickname(plugin_stopper, bot.ts3conn)
        plugin_stopper.clear()
        plugin_info.start()


@command(f"{plugin_command_name} stop")
def stop_plugin(_sender=None, _msg=None):
    """
    Stop the BadNickname by setting the plugin_stopper signal and undefining the plugin.
    """
    global plugin_info
    plugin_stopper.set()
    plugin_info = None

@command(f"{plugin_command_name} restart")
def restart_plugin(_sender=None, _msg=None):
    """
    Restarts the plugin by executing the respective functions.
    """
    stop_plugin()
    start_plugin()


@setup
def setup(ts3bot,
            auto_start = autoStart,
            enable_dry_run = dry_run,
            frequency = check_frequency,
            exclude_servergroups = servergroups_to_exclude,
            name_pattern = bad_name_pattern,
            kick_message = kick_reason_message
    ):
    global bot, autoStart, dry_run, check_frequency, servergroups_to_exclude, bad_name_pattern, kick_reason_message

    bot = ts3bot
    autoStart = auto_start
    dry_run = enable_dry_run
    check_frequency = frequency
    servergroups_to_exclude = exclude_servergroups
    bad_name_pattern = name_pattern
    kick_reason_message = kick_message

    if autoStart:
        start_plugin()


@exit
def exit_plugin():
    global plugin_info

    if plugin_info is not None:
        plugin_stopper.set()
        plugin_info.join()
        plugin_info = None
