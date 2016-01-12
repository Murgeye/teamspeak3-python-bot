import configparser
import traceback
setups = []
exits = []
event_handler = None
command_handler = None

def loadmodules(bot):
    global event_handler, command_handler
    config = configparser.ConfigParser()
    config.read('config.ini')
    plugins = config.items("Plugins")
    event_handler = bot.event_handler
    command_handler = bot.command_handler
    for plugin in plugins:
        plugmod = __import__("modules."+plugin[1])
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

def exit(function):
    exits.append(function)

def exit_all():
    for exit in exits:
        exit()

def reload():
    exit_all()
