"""AfkMover Module for the Teamspeak3 Bot."""
import threading
import traceback
from threading import Thread

import ts3API.Events as Events
from ts3API.TS3Connection import TS3QueryException
from ts3API.utilities import TS3Exception

from Moduleloader import *
import Bot
from typing import Union

plugin_version = 0.1
plugin_command_name = "afkmover"
afkMover: Union[None, 'AfkMover'] = None
afkStopper = threading.Event()
bot: Bot.Ts3Bot

# defaults for configureable options
autoStart = True
dry_run = False # log instead of performing actual actions
check_frequency = 30.0
servergroups_to_exclude = None
enable_auto_move_back = True
resp_channel_settings = True
fallback_action = None
channel_name = "AFK"

class AfkMover(Thread):
    """
    AfkMover class. Moves clients set to afk another channel.
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
        Create a new AfkMover object.
        :param stop_event: Event to signalize the AfkMover to stop moving.
        :type stop_event: threading.Event
        :param ts3conn: Connection to use
        :type: TS3Connection
        """
        Thread.__init__(self)
        self.stopped = stop_event
        self.ts3conn = ts3conn
        self.afk_channel = self.get_channel_by_name(channel_name)
        self.client_channels = {}
        self.update_servergroup_ids_list()
        self.afk_list = None
        if self.afk_channel is None:
            AfkMover.logger.error("Could not get afk channel")


    def get_channel_by_name(self, name="AFK"):
        """
        Get the channel id of the channel specified by name.
        :param name: Channel name
        :return: Channel id
        """
        try:
            channel = self.ts3conn.channelfind(name)[0].get("cid", '-1')
        except TS3Exception:
            AfkMover.logger.exception("Error getting afk channel")
            raise
        return channel


    def update_afk_list(self):
        """
        Update the list of clients.
        """
        try:
            self.afk_list = self.ts3conn.clientlist(["away"])
            AfkMover.logger.debug("Awaylist: " + str(self.afk_list))
        except TS3Exception:
            AfkMover.logger.exception("Error getting away list!")
            self.afk_list = list()


    def get_back_list(self):
        """
        Get list of clients in the afk channel, but not away.
        :return: List of clients who are back from afk.
        """
        clientlist = [client for client in self.afk_list if client.get("client_away", '1') == '0'
                      and int(client.get("cid", '-1')) == int(self.afk_channel)]
        return clientlist

    def fallback_action(self, client_id):
        """
        In case if a client couldn't be moved, this function decides if the user should simply stay in the
        AFK channel or if he should be moved to an alternative channel.
        :param client_id: The client ID, which should be moved
        """
        if fallback_action is None or fallback_action == "None":
            return
        else:
            channel_name = str(fallback_action)

        try:
            self.ts3conn.clientmove(self.get_channel_by_name(channel_name), client_id)
            del self.client_channels[client_id]
        except KeyError:
            AfkMover.logger.error(f"Error moving client! clid={client_id} not found in {str(self.client_channels)}")
        except TS3Exception:
            AfkMover.logger.exception(f"Error moving client! clid={client_id}")

    def move_all_back(self):
        """
        Move all clients who are back from afk.
        """
        back_list = self.get_back_list()
        if back_list is None:
            AfkMover.logger.debug("move_all_back back list is empty. Nothing todo.")
            return

        AfkMover.logger.debug("Moving clients back")
        AfkMover.logger.debug("Backlist is: %s", str(back_list))
        AfkMover.logger.debug("Saved channel list keys are: %s\n", str(self.client_channels.keys()))

        try:
            channel_list = self.ts3conn.channellist()
        except TS3QueryException as e:
            AfkMover.logger.error(f"Failed to get the current channellist: {str(e.message)}")
            return

        for client in back_list:
            if client.get("clid", -1) not in self.client_channels.keys():
                continue

            AfkMover.logger.info("Moving a client back!")
            AfkMover.logger.debug("Client: " + str(client))
            AfkMover.logger.debug("Saved channel list keys:" + str(self.client_channels))

            channel_id = int(self.client_channels.get(client.get("clid", -1)))
            client_id = int(client.get("clid", '-1'))

            try:
                channel_info = self.ts3conn._parse_resp_to_dict(self.ts3conn._send("channelinfo", [f"cid={channel_id}"]))
            except TS3QueryException as e:
                # Error: invalid channel ID (channel ID does not exist (anymore))
                if int(e.id) == 768:
                    AfkMover.logger.error(f"Failed to get channelinfo as the channel does not exist anymore: {str(client)}")
                    continue

            channel_details = None
            for channel in channel_list:
                if int(channel['cid']) == channel_id:
                    channel_details = channel
                    break

            if resp_channel_settings and channel_details is not None:
                if int(channel_info.get("channel_maxclients")) != -1 and int(channel_details.get("total_clients")) >= int(channel_info.get("channel_maxclients")):
                    AfkMover.logger.warning(f"Failed to move back the following client as the channel has already the maximum of clients: {str(client)}")
                    self.fallback_action(client_id)
                    continue

                if int(channel_info.get("channel_flag_password")):
                    AfkMover.logger.warning(f"Failed to move back the following client as the channel has a password: {str(client)}")
                    self.fallback_action(client_id)
                    continue

            try:
                self.ts3conn.clientmove(channel_id, client_id)

                del self.client_channels[client_id]
            except TS3QueryException as e:
                # Error: invalid channel ID (channel ID does not exist (anymore))
                if int(e.id) == 768:
                    AfkMover.logger.error(f"Failed to move back the following client as the old channel does not exist anymore: {str(client)}")
                # Error: channel maxclient or maxfamily reached
                if int(e.id) in (777, 778):
                    AfkMover.logger.error(f"Failed to move back the following client as the old channel has already the maximum of clients: {str(client)}")
                # Error: invalid channel password
                if int(e.id) == 781:
                    AfkMover.logger.error(f"Failed to move back the following client as the old channel has an unknown password: {str(client)}")
                else:
                    AfkMover.logger.exception(f"Failed to move back the following client: {str(client)}")

                self.fallback_action(client_id)


    def update_servergroup_ids_list(self):
        """
        Updates the list of servergroup IDs, which should be ignored.
        """
        self.servergroup_ids_to_ignore = []

        if servergroups_to_exclude is None:
            AfkMover.logger.debug(f"No servergroups to exclude defined. Nothing todo.")
            return

        try:
            servergroup_list = self.ts3conn.servergrouplist()
        except TS3QueryException:
            AfkMover.logger.exception(f"Failed to get the list of available servergroups.")

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
            AfkMover.logger.exception(f"Failed to get the list of assigned servergroups for the client cldbid={cldbid}.")
            return client_servergroup_ids

        for servergroup in client_servergroups:
            client_servergroup_ids.append(servergroup.get("sgid"))

        AfkMover.logger.debug(f"client_database_id={cldbid} has these servergroups: {str(client_servergroup_ids)}")

        return client_servergroup_ids


    def get_away_list(self):
        """
        Get list of clients with afk status.
        :return: List of clients that are set to afk.
        """
        if self.afk_list is not None:
            AfkMover.logger.debug(str(self.afk_list))

            awaylist = list()
            for client in self.afk_list:
                AfkMover.logger.debug(str(self.afk_list))

                if "cid" not in client.keys():
                    AfkMover.logger.error("Client without cid!")
                    AfkMover.logger.error(str(client))
                    continue

                if client.get("client_type") == '1':
                    AfkMover.logger.debug(f"Ignoring ServerQuery client: {client}")
                    continue

                if servergroups_to_exclude is not None:
                    client_is_in_group = False
                    for client_servergroup_id in self.get_servergroups_by_client(client.get("client_database_id")):
                        if client_servergroup_id in self.servergroup_ids_to_ignore:
                            AfkMover.logger.debug(f"The client is in the servergroup sgid={client_servergroup_id}, which should be ignored: {client}")
                            client_is_in_group = True
                            break

                    if client_is_in_group:
                        continue

                if "client_away" not in client.keys():
                    AfkMover.logger.debug(f"The client has no `client_away` property: {client}")
                    continue

                if client.get("client_away", '0') == '0':
                    AfkMover.logger.debug(f"The client is not away: {client}")
                    continue

                if int(client.get("cid", '-1')) == int(self.afk_channel):
                    AfkMover.logger.debug(f"The client is already in the `afk_channel`: {client}")
                    continue

                awaylist.append(client)
            return awaylist
        else:
            AfkMover.logger.error("Clientlist is None!")
            return list()


    def move_to_afk(self, client_list):
        """
        Move clients to the afk_channel.
        :param client_list: List of clients to move.
        """
        if client_list is None:
            AfkMover.logger.debug("move_to_afk client list is empty. Nothing todo.")
            return

        AfkMover.logger.debug("Moving clients to afk!")

        for client in client_list:
            if dry_run:
                AfkMover.logger.debug(f"I would have moved this client: {str(client)}")
            else:
                AfkMover.logger.info("Moving somebody to afk!")
                AfkMover.logger.debug("Client: " + str(client))

                try:
                    self.ts3conn.clientmove(self.afk_channel, int(client.get("clid", '-1')))
                    self.client_channels[client.get("clid", '-1')] = client.get("cid", '0')
                except TS3Exception:
                    AfkMover.logger.exception(f"Error moving client! clid={str(client.get('clid', '-1'))}")

            AfkMover.logger.debug("Moved List after move: " + str(self.client_channels))


    def move_all_afk(self):
        """
        Move all afk clients.
        """
        try:
            afk_list = self.get_away_list()
            self.move_to_afk(afk_list)
        except AttributeError:
            AfkMover.logger.exception("Connection error!")

    def auto_move_all(self):
        """
        Loop move functions until the stop signal is sent.
        """
        while not self.stopped.wait(float(check_frequency)):
            AfkMover.logger.debug("Afkmover running!")
            try:
                self.update_afk_list()
                if enable_auto_move_back:
                    self.move_all_back()
                self.move_all_afk()
            except BaseException:
                AfkMover.logger.error("Uncaught exception:" + str(sys.exc_info()[0]))
                AfkMover.logger.error(str(sys.exc_info()[1]))
                AfkMover.logger.error(traceback.format_exc())
                AfkMover.logger.error("Saved channel list keys are: %s\n",
                                      str(self.client_channels.keys()))
        AfkMover.logger.warning("AFKMover stopped!")
        self.client_channels = {}

    def run(self):
        """
        Thread run method. Starts the mover.
        """
        AfkMover.logger.info("AFKMove Thread started")
        try:
            self.auto_move_all()
        except BaseException:
            self.logger.exception("Exception occured in run:")


@command(f"{plugin_command_name} version")
def send_version(sender=None, _msg=None):
    """
    Sends the plugin version as textmessage to the `sender`.
    """
    try:
        Bot.send_msg_to_client(bot.ts3conn, sender, f"This plugin is installed in the version `{str(plugin_version)}`.")
    except TS3Exception:
        AfkMover.logger.exception("Error while sending the plugin version as a message to the client!")


@command(f"{plugin_command_name} start")
def start_plugin(_sender=None, _msg=None):
    """
    Start the AfkMover by clearing the afkStopper signal and starting the mover.
    """
    global afkMover
    if afkMover is None:
        if dry_run:
            AfkMover.logger.info("Dry run is enabled - logging actions intead of actually performing them.")

        afkMover = AfkMover(afkStopper, bot.ts3conn)
        afkStopper.clear()
        afkMover.start()


@command(f"{plugin_command_name} stop")
def stop_plugin(_sender=None, _msg=None):
    """
    Stop the AfkMover by setting the afkStopper signal and undefining the mover.
    """
    global afkMover
    afkStopper.set()
    afkMover = None


@command(f"{plugin_command_name} restart")
def restart_plugin(_sender=None, _msg=None):
    """
    Restarts the plugin by executing the respective functions.
    """
    stop_plugin()
    start_plugin()


@event(Events.ClientLeftEvent,)
def client_left(event_data):
    """
    Clean up leaving clients.
    """
    # Forget clients that were set to afk and then left
    if afkMover is not None:
        if str(event_data.client_id) in afkMover.client_channels:
            del afkMover.client_channels[str(event_data.client_id)]


@setup
def setup(ts3bot,
            auto_start = autoStart,
            enable_dry_run = dry_run,
            frequency = check_frequency,
            exclude_servergroups = servergroups_to_exclude,
            auto_move_back = enable_auto_move_back,
            respect_channel_settings = resp_channel_settings,
            fallback_channel = fallback_action,
            channel = channel_name
    ):
    global bot, autoStart, dry_run, check_frequency, servergroups_to_exclude, enable_auto_move_back, resp_channel_settings, fallback_action, channel_name

    bot = ts3bot
    autoStart = auto_start
    dry_run = enable_dry_run
    check_frequency = frequency
    servergroups_to_exclude = exclude_servergroups
    enable_auto_move_back = auto_move_back
    resp_channel_settings = respect_channel_settings
    fallback_action = fallback_channel
    channel_name = channel

    if autoStart:
        start_plugin()


@exit
def afkmover_exit():
    global afkMover
    if afkMover is not None:
        afkStopper.set()
        afkMover.join()
        afkMover = None
