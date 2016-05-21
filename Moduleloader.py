import configparser
import traceback
import logging
setups = []
exits = []
event_handler = None
command_handler = None
logger = logging.getLogger("moduleloader")
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler("moduleloader.log", mode='a+')
formatter = logging.Formatter('Moduleloader Logger %(asctime)s %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.info("Configured Moduleloader logger")
logger.propagate = 0

def loadmodules(bot):
    global event_handler, command_handler
    config = configparser.ConfigParser()
    config.read('config.ini')
    plugins = config.items("Plugins")
    event_handler = bot.event_handler
    command_handler = bot.command_handler
    for plugin in plugins:
        try:
            plugmod = __import__("modules."+plugin[1])
            logger.info("Loaded module " + plugin[0])
        except:
            logger.exception("While loading plugin " + str(plugin[0]) + " from modules."+plugin[1])
    for setup in setups:
        setup(bot)

def setup(function):
    setups.append(function)
    return function

def event(*event_types):
    def register_observer(function):
        for event_type in event_types:
            event_handler.add_observer(function, event_type)
        return function
    return register_observer

def command(*command_list):
    def register_command(function):
        for command in command_list:
            command_handler.add_handler(function, command)
        return function
    return register_command

def group(*groups):
    def save_allowed_groups(func):
        func.allowed_groups=groups
        return func
    return save_allowed_groups

def exit(function):
    exits.append(function)

def exit_all():
    for exit in exits:
        exit()

def reload():
    exit_all()
