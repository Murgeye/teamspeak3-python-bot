# standard imports
import logging
import threading
import traceback
from threading import Thread
from typing import Union
import sys

# third-party imports
from ts3API.Events import ClientLeftEvent
from ts3API.utilities import TS3Exception

# local imports
from module_loader import setup_plugin, exit_plugin, command, event
import teamspeak_bot

PLUGIN_VERSION = 0.1
PLUGIN_COMMAND_NAME = "plugintemplate"
PLUGIN_INFO: Union[None, 'PluginTemplate'] = None
PLUGIN_STOPPER = threading.Event()
BOT: teamspeak_bot.Ts3Bot

# defaults for configureable options
AUTO_START = True
DRY_RUN = False # log instead of performing actual actions
CHECK_FREQUENCY_SECONDS = 30.0
SOME_OPTION = "someValue"

class PluginTemplate(Thread):
    """
    PluginTemplate class. A sample plugin template.
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
    logger.info("Configured %s logger", str(class_name))
    logger.propagate = 0

    def __init__(self, stop_event, ts3conn):
        """
        Create a new object of this class.
        :param stop_event: Event to signalize this plugin to stop
        :type stop_event: threading.Event
        :param ts3conn: Connection to use
        :type: TS3Connection
        """
        Thread.__init__(self)
        self.stopped = stop_event
        self.ts3conn = ts3conn
        self.client_list = None


    def update_client_list(self):
        """
        Update the list of currently connected clients.
        """
        try:
            self.client_list = self.ts3conn.clientlist()
            PluginTemplate.logger.debug("client_list: %s", str(self.client_list))
        except TS3Exception:
            PluginTemplate.logger.exception("Error while getting client list!")
            self.client_list = []


    def send_message_to_all_clients(self):
        """
        Sends a "Hello World!" message to every connected client except ServerQuery clients.
        """
        if self.client_list is None:
            PluginTemplate.logger.debug("client_list is None (empty). Looks like no real client is connected.")
            return

        for client in self.client_list:
            if 'clid' not in client:
                PluginTemplate.logger.error("Error, because the following client has no clid: %s", str(client))
                continue

            if 'client_type' not in client:
                PluginTemplate.logger.error("Error, because the following client has no client_type: %s", str(client))
                continue

            if client['client_type'] == 1:
                PluginTemplate.logger.debug("Skipping the following client as it is a ServerQuery client: %s", str(client))
                continue

            if DRY_RUN:
                PluginTemplate.logger.info("I would have sent a textmessage to this client, when dry-run would be disabled: %s", str(client))
            else:
                PluginTemplate.logger.debug("Sending the following client a message: %s", str(client))

                try:
                    teamspeak_bot.send_msg_to_client(BOT.ts3conn, client['clid'], "Hello World!")
                except AttributeError:
                    PluginTemplate.logger.exception("AttributeError: %s", str(client))
                except TS3Exception:
                    PluginTemplate.logger.exception("Error while sending a message to the client: %s", str(client))

    def loop_until_stopped(self):
        """
        Loop over all main functions with a specific delay between each execution until the stop signal is sent.
        """
        while not self.stopped.wait(float(CHECK_FREQUENCY_SECONDS)):
            PluginTemplate.logger.debug("Thread running!")
            PluginTemplate.logger.info("SOME_OPTION value: %s", str(SOME_OPTION))

            try:
                self.update_client_list()
                self.send_message_to_all_clients()
            except BaseException:
                PluginTemplate.logger.error("Uncaught exception: %s", str(sys.exc_info()[0]))
                PluginTemplate.logger.error(str(sys.exc_info()[1]))
                PluginTemplate.logger.error(traceback.format_exc())

        PluginTemplate.logger.warning("Thread stopped!")

    def run(self):
        """
        Thread run method.
        """
        PluginTemplate.logger.info("Thread started!")
        try:
            self.loop_until_stopped()
        except BaseException:
            self.logger.exception("Exception occured in run:")


@command(f"{PLUGIN_COMMAND_NAME} version")
def send_version(sender=None, _msg=None):
    """
    Sends the plugin version as textmessage to the `sender`.
    """
    try:
        teamspeak_bot.send_msg_to_client(BOT.ts3conn, sender, f"This plugin is installed in the version `{str(PLUGIN_VERSION)}`.")
    except TS3Exception:
        PluginTemplate.logger.exception("Error while sending the plugin version as a message to the client!")


@command(f"{PLUGIN_COMMAND_NAME} start")
def start_plugin(_sender=None, _msg=None):
    """
    Start the plugin by clearing the respective signal and starting it.
    """
    global PLUGIN_INFO
    if PLUGIN_INFO is None:
        if DRY_RUN:
            PluginTemplate.logger.info("Dry run is enabled - logging actions intead of actually performing them.")

        PLUGIN_INFO = PluginTemplate(PLUGIN_STOPPER, BOT.ts3conn)
        PLUGIN_STOPPER.clear()
        PLUGIN_INFO.run()

        PluginTemplate.logger.info("Started plugin!")


@command(f"{PLUGIN_COMMAND_NAME} stop")
def stop_plugin(_sender=None, _msg=None):
    """
    Stop the plugin by setting the respective signal and undefining it.
    """
    global PLUGIN_INFO
    PLUGIN_STOPPER.set()
    PLUGIN_INFO = None

    PluginTemplate.logger.info("Stopped plugin!")


@command(f"{PLUGIN_COMMAND_NAME} restart")
def restart_plugin(_sender=None, _msg=None):
    """
    Restarts the plugin by executing the respective functions.
    """
    stop_plugin()
    start_plugin()


@event(ClientLeftEvent)
def client_left_event(event_data):
    """
    Do something, when a client left the TeamSpeak server.
    """
    if PLUGIN_INFO is not None:
        PluginTemplate.logger.info("ClientLeftEvent: %s", str(event_data))


@setup_plugin
def setup(ts3bot, auto_start = AUTO_START, enable_dry_run = DRY_RUN, frequency = CHECK_FREQUENCY_SECONDS, some_option = SOME_OPTION):
    """
    Sets up this plugin.
    """
    global BOT, AUTO_START, DRY_RUN, CHECK_FREQUENCY_SECONDS, SOME_OPTION
    BOT = ts3bot
    AUTO_START = auto_start
    DRY_RUN = enable_dry_run
    CHECK_FREQUENCY_SECONDS = frequency
    SOME_OPTION = some_option
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
