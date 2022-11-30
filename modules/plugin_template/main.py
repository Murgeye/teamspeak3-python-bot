import threading
import traceback
from threading import Thread

import ts3API.Events as Events
from ts3API.utilities import TS3Exception

from Moduleloader import *
import Bot
from typing import Union

pluginInfo: Union[None, 'PluginTemplate'] = None
pluginStopper = threading.Event()
bot: Bot.Ts3Bot

# defaults for configureable options
autoStart = True
dry_run = False # log instead of performing actual actions
check_frequency = 30.0
some_option = "someValue"

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
    logger.info(f"Configured {class_name} logger")
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
            PluginTemplate.logger.debug("client_list: " + str(self.client_list))
        except TS3Exception:
            PluginTemplate.logger.exception("Error while getting client list!")
            self.client_list = list()


    def send_message_to_all_clients(self):
        """
        Sends a "Hello World!" message to every connected client except ServerQuery clients.
        """
        if self.client_list is not None:
            for client in self.client_list:
                if 'clid' not in client:
                    PluginTemplate.logger.debug(f"Skipping the following client as it has no clid: {client}")
                    continue

                if 'client_type' not in client:
                    PluginTemplate.logger.debug(f"Skipping the following client as it has no client_type: {client}")
                    continue

                if client['client_type'] == 1:
                    PluginTemplate.logger.debug(f"Skipping the following client as it is a ServerQuery client: {client}")
                    continue

                PluginTemplate.logger.debug(f"Sending the following client a message: {client}")
                if not dry_run:
                    try:
                        Bot.send_msg_to_client(bot.ts3conn, client['clid'], "Hello World!")
                    except AttributeError:
                        PluginTemplate.logger.exception(f"AttributeError: {client}")
                    except TS3Exception:
                        PluginTemplate.logger.exception("Error while sending a message to clients!")
        else:
            PluginTemplate.logger.debug("client_list is None (empty). Looks like no real client is connected.")

    def loop_until_stopped(self):
        """
        Loop over all main functions with a specific delay between each execution until the stop signal is sent.
        """
        while not self.stopped.wait(float(check_frequency)):
            PluginTemplate.logger.debug("Thread running!")
            PluginTemplate.logger.debug(f"some_option value: {some_option}")

            try:
                self.update_client_list()
                self.send_message_to_all_clients()
            except BaseException:
                PluginTemplate.logger.error("Uncaught exception:" + str(sys.exc_info()[0]))
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


@command('startplugintemplate')
def start_plugin(_sender=None, _msg=None):
    """
    Start the plugin by clearing the respective signal and starting it.
    """
    global pluginInfo
    if pluginInfo is None:
        if dry_run:
            PluginTemplate.logger.info("Dry run is enabled - logging actions intead of actually performing them.")

        pluginInfo = PluginTemplate(pluginStopper, bot.ts3conn)
        pluginStopper.clear()
        pluginInfo.run()


@command('stopplugintemplate')
def stop_plugin(_sender=None, _msg=None):
    """
    Stop the plugin by setting the respective signal and undefining it.
    """
    global pluginInfo
    pluginStopper.set()
    pluginInfo = None


@event(Events.ClientLeftEvent)
def client_left_event(event_data):
    """
    Do something, when a client left the TeamSpeak server.
    """
    if pluginInfo is not None:
         PluginTemplate.logger.info(f"ClientLeftEvent: {str(event_data)}")


@setup
def setup(ts3bot, auto_start = autoStart, enable_dry_run = dry_run, frequency = check_frequency, someOption = some_option):
    global bot, autoStart, dry_run, check_frequency, some_option
    bot = ts3bot
    autoStart = auto_start
    dry_run = enable_dry_run
    check_frequency = frequency
    some_option = someOption
    if autoStart:
        start_plugin()


@exit
def exit_plugin():
    global pluginInfo
    if pluginInfo is not None:
        pluginStopper.set()
        pluginInfo.join()
        pluginInfo = None
