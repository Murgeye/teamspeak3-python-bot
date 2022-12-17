# standard imports
import logging
import threading
import traceback
from threading import Thread
from typing import Union
import sys

from urllib import request, error
import json
from datetime import datetime, timedelta

# third-party imports
from ts3API.TS3Connection import TS3QueryException
from ts3API.utilities import TS3Exception

# local imports
from module_loader import setup_plugin, exit_plugin, command
import teamspeak_bot
import client_info

PLUGIN_VERSION = 0.1
PLUGIN_COMMAND_NAME = "twitchlive"
PLUGIN_INFO: Union[None, "TwitchLive"] = None
PLUGIN_STOPPER = threading.Event()
BOT: teamspeak_bot.Ts3Bot

# defaults for configureable options
AUTO_START = True
DRY_RUN = False  # log instead of performing actual actions
CHECK_FREQUENCY_SECONDS = 5.0
SERVERGROUP_NAME = None  # The servergroup name, which should get un-/assigned from/to clients based on their Twitch stream status
API_CLIENT_ID = None  # The Twitch API client ID
API_CLIENT_SECRET = None  # The Twitch API client secret


class TwitchLive(Thread):
    """
    TwitchLive class. Assigns or unassigns a specific servergroup to or from a client depending on their Twitch stream status.
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
        Create a new TwitchLive object.
        :param stop_event: Event to signalize the TwitchLive to stop.
        :type stop_event: threading.Event
        :param ts3conn: Connection to use
        :type: TS3Connection
        """
        Thread.__init__(self)
        self.stopped = stop_event
        self.ts3conn = ts3conn
        self.live_servergroup_id = self.get_servergroup_by_name(SERVERGROUP_NAME)
        self.twitch_api_client_id = API_CLIENT_ID
        self.twitch_api_access_token = None
        self.twitch_api_expires_at = None

    def run(self):
        """
        Thread run method. Starts the plugin.
        """
        TwitchLive.logger.info("Thread started")
        try:
            self.loop_until_stopped()
        except BaseException:
            self.logger.exception("Exception occured in run:")

    def get_servergroup_by_name(self, name="live"):
        """
        Get the servergroup id of the servergroup specified by name.
        :param name: servergroup name
        :return: servergroup id
        """
        try:
            servergroup_id = self.ts3conn.find_servergroup_by_name(name).get("sgid")
        except TS3Exception:
            TwitchLive.logger.exception(
                "Error while finding a servergroup with the name `%s`.", str(name)
            )
            raise

        return servergroup_id

    def get_oauth_access_token(self):
        """
        Get a OAuth Access Token for the Twitch API.
        """
        if (
            self.twitch_api_expires_at is not None
            and (self.twitch_api_expires_at - datetime.now()).total_seconds() > 60 * 5
        ):
            TwitchLive.logger.debug(
                "The Twitch API OAuth Access Token is still valid. No renewal required."
            )
            return

        TwitchLive.logger.info("Requesting a new Twitch API OAuth Access Token...")

        api_request = request.Request(
            f"https://id.twitch.tv/oauth2/token?client_id={API_CLIENT_ID}&client_secret={API_CLIENT_SECRET}&grant_type=client_credentials",
            method="POST",
        )

        try:
            with request.urlopen(api_request) as api_response:
                api_response = json.load(api_response)
                self.twitch_api_access_token = api_response["access_token"]
                self.twitch_api_expires_at = datetime.now() + timedelta(
                    seconds=api_response["expires_in"]
                )
        except error.HTTPError:
            TwitchLive.logger.exception(
                "Failed to get a new Twitch API OAuth Access Token."
            )
            raise

        TwitchLive.logger.info(
            "Got a new Twitch API OAuth Access Token. Expires at %s.",
            str(self.twitch_api_expires_at),
        )

    def get_client_list(self):
        """
        Get list of connected clients.
        :return: List of connected clients.
        """
        client_list = []

        try:
            for client in self.ts3conn.clientlist():
                if int(client.get("client_type")) == 1:
                    TwitchLive.logger.debug(
                        "update_client_list ignoring ServerQuery client: %s",
                        str(client),
                    )
                    continue

                client_list.append(client)

            TwitchLive.logger.debug("client_list: %s", str(client_list))
        except TS3Exception:
            TwitchLive.logger.exception("Error getting client list!")

        return client_list

    def get_clients_with_a_description(self):
        """
        Get clients, which have a description set.
        :return: List of clients with a set description.
        :type list[dict]
        """
        client_list = []

        try:
            for client in self.get_client_list():
                client_description = str(
                    client_info.ClientInfo(client.get("clid"), self.ts3conn).description
                )

                if not client_description:
                    TwitchLive.logger.debug(
                        "The client clid=%s client_nickname=%s has no `client_description`.",
                        int(client.get("clid")),
                        str(client.get("client_nickname")),
                    )
                    continue

                client_list.append(
                    {
                        "clid": client.get("clid"),
                        "client_database_id": client.get("client_database_id"),
                        "client_description": str(client_description),
                    }
                )
        except TS3Exception:
            TwitchLive.logger.exception("Error getting client list!")

        TwitchLive.logger.debug("client_list: %s", str(client_list))

        return client_list

    def get_twitch_streamer_user_id(self, client_description):
        """
        Get the Twitch streamer user ID of a client.
        :param client_description: Twitch Streamer URL or login name
        :return: Twitch Streamer User ID
        """
        TwitchLive.logger.debug(
            "Getting Twitch streamer user ID from `%s`.", str(client_description)
        )

        twitch_login = client_description.replace("https://www.twitch.tv/", "")
        TwitchLive.logger.debug(
            "Getting Twitch streamer user ID for `login` `%s`.", str(twitch_login)
        )

        api_request = request.Request(
            f"https://api.twitch.tv/helix/users?login={twitch_login}", method="GET"
        )
        api_request.add_header(
            "Authorization", f"Bearer {self.twitch_api_access_token}"
        )
        api_request.add_header("Client-Id", str(self.twitch_api_client_id))

        twitch_streamer_user_id = None

        try:
            with request.urlopen(api_request) as api_response:
                api_response = json.load(api_response)
                twitch_streamer_user_id = api_response["data"][0]["id"]
        except error.HTTPError:
            TwitchLive.logger.exception("Failed to get a Twitch streamer user ID.")
            raise

        TwitchLive.logger.debug(
            "Got a Twitch streamer user ID: %s.", int(twitch_streamer_user_id)
        )

        return twitch_streamer_user_id

    def get_servergroup_ids_by_client(self, cldbid):
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
            TwitchLive.logger.exception(
                "Failed to get the list of assigned servergroups for the client cldbid=%s.",
                int(cldbid),
            )
            return client_servergroup_ids

        for servergroup in client_servergroups:
            client_servergroup_ids.append(servergroup.get("sgid"))

        TwitchLive.logger.debug(
            "client_database_id=%s has these servergroups: %s",
            int(cldbid),
            str(client_servergroup_ids),
        )

        return client_servergroup_ids

    def manage_live_status(self, client):
        """
        Checks if the Twitch streamer is currently online or offline and assigns or removes the respective servergroup to / from the client.
        :param client: Client information (clid, Twitch user Id)
        """
        TwitchLive.logger.debug(
            "Getting online status of Twitch streamer: `%s`", str(client)
        )

        api_request = request.Request(
            f"https://api.twitch.tv/helix/streams?user_id={client['twitch_user_id']}",
            method="GET",
        )
        api_request.add_header(
            "Authorization", f"Bearer {self.twitch_api_access_token}"
        )
        api_request.add_header("Client-Id", str(self.twitch_api_client_id))

        twitch_stream_online = False

        try:
            with request.urlopen(api_request) as api_response:
                api_response = json.load(api_response)
        except error.HTTPError:
            TwitchLive.logger.exception(
                "Failed to get stream information for Twitch streamer: {str(client)}"
            )
            raise

        if (
            len(api_response["data"])
            and api_response["data"][0]["type"].lower() == "live"
        ):
            twitch_stream_online = True

        client_assigned_servergroup_ids = self.get_servergroup_ids_by_client(
            client["client_database_id"]
        )

        if twitch_stream_online:
            TwitchLive.logger.debug("Twitch stream is online!")

            if self.live_servergroup_id not in client_assigned_servergroup_ids:
                if DRY_RUN:
                    TwitchLive.logger.info(
                        "Twitch streamer is online. I would have assigned client_database_id=%s the respective servergroup.",
                        int(client["client_database_id"]),
                    )
                else:
                    TwitchLive.logger.info(
                        "Twitch streamer is online. Assigning client_database_id=%s the respective servergroup.",
                        int(client["client_database_id"]),
                    )

                    try:
                        self.ts3conn._send(
                            "servergroupaddclient",
                            [
                                f"sgid={self.live_servergroup_id}",
                                f"cldbid={client['client_database_id']}",
                            ],
                        )
                    except TS3Exception:
                        TwitchLive.logger.exception(
                            "Failed to assign the servergroup to the client_database_id=%s.",
                            int(client["client_database_id"]),
                        )
                        raise
        else:
            TwitchLive.logger.debug("Twitch stream is offline!")

            if self.live_servergroup_id in client_assigned_servergroup_ids:
                if DRY_RUN:
                    TwitchLive.logger.info(
                        "Twitch streamer is offline. I would have removed client_database_id=%s from the respective servergroup.",
                        int(client["client_database_id"]),
                    )
                else:
                    TwitchLive.logger.info(
                        "Twitch streamer is offline. Removing client_database_id=%s from the respective servergroup.",
                        int(client["client_database_id"]),
                    )

                    try:
                        self.ts3conn._send(
                            "servergroupdelclient",
                            [
                                f"sgid={self.live_servergroup_id}",
                                f"cldbid={client['client_database_id']}",
                            ],
                        )
                    except TS3Exception:
                        TwitchLive.logger.exception(
                            "Failed to remove the servergroup from the client_database_id=%s.",
                            int(client["client_database_id"]),
                        )
                        raise

    def loop_until_stopped(self):
        """
        Loop move functions until the stop signal is sent.
        """
        while not self.stopped.wait(float(CHECK_FREQUENCY_SECONDS)):
            TwitchLive.logger.debug("Thread running!")

            try:
                self.get_oauth_access_token()
                for client in self.get_clients_with_a_description():
                    client["twitch_user_id"] = self.get_twitch_streamer_user_id(
                        client.get("client_description")
                    )
                    self.manage_live_status(client)
            except BaseException:
                TwitchLive.logger.error(
                    "Uncaught exception: %s", str(sys.exc_info()[0])
                )
                TwitchLive.logger.error(str(sys.exc_info()[1]))
                TwitchLive.logger.error(traceback.format_exc())

        TwitchLive.logger.warning("Thread stopped!")


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
        TwitchLive.logger.exception(
            "Error while sending the plugin version as a message to the client!"
        )


@command(f"{PLUGIN_COMMAND_NAME} start")
def start_plugin(_sender=None, _msg=None):
    """
    Start the TwitchLive by clearing the PLUGIN_STOPPER signal and starting the plugin.
    """
    global PLUGIN_INFO
    if PLUGIN_INFO is None:
        if DRY_RUN:
            TwitchLive.logger.info(
                "Dry run is enabled - logging actions intead of actually performing them."
            )

        PLUGIN_INFO = TwitchLive(PLUGIN_STOPPER, BOT.ts3conn)
        PLUGIN_STOPPER.clear()
        PLUGIN_INFO.start()


@command(f"{PLUGIN_COMMAND_NAME} stop")
def stop_plugin(_sender=None, _msg=None):
    """
    Stop the TwitchLive by setting the PLUGIN_STOPPER signal and undefining the plugin.
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
    twitch_live_servergroup_name=SERVERGROUP_NAME,
    twitch_api_client_id=API_CLIENT_ID,
    twitch_api_client_secret=API_CLIENT_SECRET,
):
    """
    Sets up this plugin.
    """
    global BOT, AUTO_START, DRY_RUN, CHECK_FREQUENCY_SECONDS, SERVERGROUP_NAME, API_CLIENT_ID, API_CLIENT_SECRET

    BOT = ts3bot
    AUTO_START = auto_start
    DRY_RUN = enable_dry_run
    CHECK_FREQUENCY_SECONDS = frequency
    SERVERGROUP_NAME = twitch_live_servergroup_name
    API_CLIENT_ID = twitch_api_client_id
    API_CLIENT_SECRET = twitch_api_client_secret

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
