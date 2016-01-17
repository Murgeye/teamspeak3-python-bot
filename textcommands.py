from ts3.TS3Connection import TS3QueryException

__author__ = 'Fabian'
import ClientInfo
import ts3.Events as Events
from importlib import reload
import threading
import logging
import Bot
import re
import Moduleloader

logger = logging.getLogger("bot")

class CommandHandler:
    def __init__(self, ts3conn):
        self.ts3conn = ts3conn
        self.logger = logging.getLogger("textMsg")
        self.logger.setLevel(logging.INFO)
        file_handler = logging.FileHandler("msg.log", mode='a+')
        formatter = logging.Formatter('MSG Logger %(asctime)s %(message)s')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        self.logger.propagate = 0
        self.handlers = {}
        self.accept_from_groups=['Moderator']

    def add_handler(self, handler, command):
        if self.handlers.get(command) is None:
            self.handlers[command]=[handler]
        else:
            self.handlers[command].append(handler)

    def handle_command(self, msg, sender=0):
        logger.debug("Handling message " + msg)
        if "!reload" in msg:
            Moduleloader.reload(afkmover)
            reload(ClientInfo)
            reload(Events)
        elif '!stop' == msg:
            Moduleloader.exit_all()
            self.ts3conn.quit()
            logger.warning("Bot was quit!")
        elif '!restart' == msg:
            Moduleloader.exit_all()
            self.ts3conn.quit()
            logger.warning("Bot was quit!")
            import main
            main.restart_program()
        else:
            command = msg.split(None,1)[0]
            if len(command)>1:
                command = command[1:]
                handlers = self.handlers.get(command)
                if handlers is not None:
                    for handler in handlers:
                        handler(sender, msg)
                else:
                    Bot.send_msg_to_client(self.ts3conn, sender, "I cannot interpret your command. I am very sorry. :(")
                    logger.info("Unknown command " + msg + " received!")

    def inform(self, event):
        if type(event) is Events.TextMessageEvent:
            if event.targetmode == "Private":
                if event.invoker_id != int(self.ts3conn.whoami()["client_id"]):  # Don't talk to yourself ...
                    ci = ClientInfo.ClientInfo(event.invoker_id, self.ts3conn)
                    self.logger.info("Message: " + event.message + " from: " + ci.name)
                    for group in self.accept_from_groups:
                        if ci.is_in_servergroups(group):
                            self.handle_command(event.message, sender=event.invoker_id)
                            return
                        Bot.send_msg_to_client(self.ts3conn, event.invoker_id, "Sorry, but I will only talk to admins!")
