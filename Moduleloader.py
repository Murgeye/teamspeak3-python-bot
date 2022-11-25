import importlib
import logging
import sys

from CommandHandler import CommandHandler
from EventHandler import EventHandler

setups = []
exits = []
plugin_modules = {}
event_handler: 'EventHandler'
command_handler: 'CommandHandler'
logger = logging.getLogger("moduleloader")
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler("logs/moduleloader.log", mode='a+')
formatter = logging.Formatter('%(asctime)s %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.info("Configured moduleloader logger")
logger.propagate = 0


# We really really want to catch all Exception here to prevent a bad module crashing the
# whole Bot
# noinspection PyBroadException,PyPep8
def load_modules(bot, config):
    """
    Load modules specified in the Plugins section of config.ini.
    :param bot: Bot to pass to the setup function of the modules
    :param config: Main bot config with plugins section
    """
    global event_handler, command_handler
    plugins = config.pop('Plugins')
    event_handler = bot.event_handler
    command_handler = bot.command_handler

    for plugin in plugins.items():
        try:
            plugin_modules[plugin[0]] = importlib.import_module(f"modules.{plugin[1]}", package="modules")
            plugin_modules[plugin[0]].pluginname = plugin[0]
            logger.info(f"Loaded module {plugin[1]}")
        except BaseException:
            logger.exception(f"Error while loading plugin {str(plugin[0])} from modules.{plugin[1]}")

    # Call all registered setup functions
    for setup_func in setups:
        try:
            name = sys.modules.get(setup_func.__module__).pluginname
            if name in config:
                plugin_config = config.pop(name)
                logger.info(f"{name} plugin config: {plugin_config}")
                setup_func(ts3bot=bot, **plugin_config)
            else:
                logger.info(f"{name} has no plugin config. Using defaults.")
                setup_func(bot)
        except BaseException:
            logger.exception(f"Error while setting up the module {name}.")


def setup(function):
    """
    Decorator for registering the setup function of a module.
    :param function: Function to register as setup
    :return:
    """
    setups.append(function)
    return function


def event(*event_types):
    """
    Decorator to register a function as an eventlistener for the event types specified in
    event_types.
    :param event_types: Event types to listen to
    :type event_types: TS3Event
    """
    def register_observer(function):
        for event_type in event_types:
            event_handler.add_observer(function, event_type)
        return function
    return register_observer


def command(*command_list):
    """
    Decorator to register a function as a handler for text commands.
    :param command_list: Commands to handle.
    :type command_list: str
    :return:
    """
    def register_command(function):
        for text_command in command_list:
            command_handler.add_handler(function, text_command)
        return function
    return register_command


def group(*groups):
    """
    Decorator to specify which groups are allowed to use the commands specified for this function.
    :param groups: List of server groups that are allowed to use the commands associated with this
    function.
    :type groups: str
    """
    def save_allowed_groups(func):
        func.allowed_groups = groups
        return func
    return save_allowed_groups


def exit(function):
    """
    Decorator to mark a function to be called upon module exit.
    :param function: Exit function to call.
    """
    exits.append(function)


# We really really want to catch all Exception here to prevent a bad module preventing everything
# else from exiting
# noinspection PyBroadException
def exit_all():
    """
    Exit all modules by calling their exit function.
    """
    for exit_func in exits:
        try:
            exit_func()
        except BaseException:
            logger.exception(f"Error while exiting the module {exit_func}.")
