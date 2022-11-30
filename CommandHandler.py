"""Commandhandler for the Teamspeak3 Bot."""
import logging

import ts3API.Events as Events

import Bot
import ClientInfo

logger = logging.getLogger("bot")


class CommandHandler:
    """
    Command handler class that listens for PrivateMessages and informs registered handlers of possible commands.
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

    def __init__(self, ts3conn):
        """
        Create new CommandHandler.
        :param ts3conn: TS3Connection to use
        """
        self.handlers = {}
        self.ts3conn = ts3conn
        # Default groups if group not specified.
        self.accept_from_groups = ['Server Admin', 'Moderator']

    def add_handler(self, handler, command):
        """
        Add a handler for a command.
        :param handler: Handler function to add.
        :type handler: function
        :param command: Command to handle.
        :type command: str
        """
        if self.handlers.get(command) is None:
            self.handlers[command] = [handler]
        else:
            self.handlers[command].append(handler)

    def check_permission(self, handler, clientinfo):
        """
        Check if the client is allowed to call this command for this handler.
        :param handler: Handler function to check permissions for.
        :param clientinfo: Client info of the client that tries to use the command.
        :return:
        """
        if hasattr(handler, "allowed_groups"):
            for group in handler.allowed_groups:
                if clientinfo.is_in_servergroups(group):
                    return True
        else:
            for group in self.accept_from_groups:
                if clientinfo.is_in_servergroups(group):
                    return True
        return False

    def handle_command(self, msg, sender=0):
        """
        Handle a new command by informing the corresponding handlers.
        :param msg: Command message.
        :param sender: Client id of the sender.
        """
        command = msg
        logger.debug(f"`clid={str(sender)}` sent a command: {str(command)}")
        if len(command) > 1:
            command = command[1:]
            handlers = self.handlers.get(command)
            ci = ClientInfo.ClientInfo(sender, self.ts3conn)
            handled = False 
            if handlers is not None:
                for handler in handlers:
                    if self.check_permission(handler, ci):
                        handled = True
                        handler(sender, msg)
                if not handled:
                    Bot.send_msg_to_client(self.ts3conn, sender, "You are not allowed to use this command!")
            else:
                Bot.send_msg_to_client(self.ts3conn, sender, "I cannot interpret your command. I am very sorry. :(")
                Bot.send_msg_to_client(self.ts3conn, sender, "Use `!help` to get a list of available commands.")
                logger.info(f"`clid={sender}` sent an unknown command: {str(command)}")

    def inform(self, event):
        """
        Inform the EventHandler of a new event.
        :param event:  New event.
        """
        if type(event) is Events.TextMessageEvent:
            if event.targetmode == "Private":
                if event.invoker_id != int(self.ts3conn.whoami()["client_id"]):  # Don't talk to yourself ...
                    ci = ClientInfo.ClientInfo(event.invoker_id, self.ts3conn)
                    self.logger.info(f"`{str(ci.name)}` wrote the following message: {str(event.message)}")
                    self.handle_command(event.message, sender=event.invoker_id)
