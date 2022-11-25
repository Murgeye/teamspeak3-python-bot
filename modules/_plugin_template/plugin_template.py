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
autoStart = True

class PluginTemplate(Thread):
    """
    PluginTemplate class. A sample plugin template.
    """

    # configure logger
    class_name = __qualname__
    logger = logging.getLogger(class_name)
    logger.propagate = 0
    logger.setLevel(logging.DEBUG)
    file_handler = logging.FileHandler(f"logs/{class_name}.log", mode='a+')
    formatter = logging.Formatter('%(asctime)s %(message)s')
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

    def send_message_to_all_clients(self):
        try:
            for client in self.ts3conn.clientlist():
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
                Bot.send_msg_to_client(bot.ts3conn, client['clid'], "Hello World!")
        except AttributeError:
            PluginTemplate.logger.exception(f"AttributeError: {client}")
        except TS3Exception:
            PluginTemplate.logger.exception("Error while sending a message to clients!")


    def run(self):
        """
        Loop over all main functions with a specific delay between each execution until the stop signal is sent.
        """
        while not self.stopped.wait(10.0):
            PluginTemplate.logger.debug(f"{PluginTemplate.class_name} running!")

            try:
                self.send_message_to_all_clients()
            except BaseException:
                PluginTemplate.logger.error("Uncaught exception:" + str(sys.exc_info()[0]))
                PluginTemplate.logger.error(str(sys.exc_info()[1]))
                PluginTemplate.logger.error(traceback.format_exc())

        PluginTemplate.logger.warning(f"{PluginTemplate.class_name} stopped!")


@command('startplugintemplate')
def start_plugin(_sender=None, _msg=None):
    """
    Start the plugin by clearing the respective signal and starting it.
    """
    global pluginInfo
    if pluginInfo is None:
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
def setup(ts3bot):
    global bot
    bot = ts3bot
    if autoStart:
        start_plugin()


@exit
def exit_plugin():
    global pluginInfo
    if pluginInfo is not None:
        pluginStopper.set()
        pluginInfo.join()
        pluginInfo = None
