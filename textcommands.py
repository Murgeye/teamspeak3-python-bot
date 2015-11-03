from ts3.TS3Connection import TS3QueryException

__author__ = 'Fabian'
import afkmover
import ClientInfo
import ts3.Events as Events
from importlib import reload
import threading
import logging
import Bot
import re
import Quotes

logger = logging.getLogger("bot")


def send_msg(ts3conn, msg):
    ts3conn.sendtextmessage(targetmode=2, target=1, msg=msg)


class CommandHandler:
    def __init__(self, ts3conn):
        self.ts3conn = ts3conn
        self.afkStopper = threading.Event()
        self.afkMover = None
        self.logger = logging.getLogger("textMsg")
        self.logger.setLevel(logging.INFO)
        file_handler = logging.FileHandler("msg.log", mode='a+')
        formatter = logging.Formatter('MSG Logger %(asctime)s %(message)s')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        self.logger.propagate = 0

    def start_afkmover(self):
        if self.afkMover is None:
            self.afkMover = afkmover.AfkMover(self.afkStopper, self.ts3conn)
            self.afkStopper.clear()
            self.afkMover.start()
            logger.info("Started afkmover!")

    def handle_command(self, msg, sender=0):
        logger.debug("Handling message " + msg)
        if "!reload" in msg:
            reload(afkmover)
            reload(ClientInfo)
            reload(Events)
        elif msg.startswith("!multimove "):
            self.multi_move(msg, sender)
        elif "!hello" in msg:
            Bot.send_msg_to_client(self.ts3conn, sender, "Hello World")
        elif '!stop' == msg:
            self.afkStopper.set()
            self.afkMover.join()
            self.ts3conn.quit()
            logger.warning("Bot was quit!")
        elif '!restart' == msg:
            self.afkStopper.set()
            self.afkMover = None
            self.ts3conn.quit()
            logger.warning("Bot was quit!")
            import main
            main.restart_program()
        elif '!client' == msg:
            logger.info("client command issued")
            Bot.send_msg_to_client(self.ts3conn, sender, "Client!")
        elif '!afkmove' in msg:
            self.start_afkmover()
        elif "!afkstop" in msg:
            logger.info("Afkstop command received")
            self.afkStopper.set()
            self.afkMover = None
            logger.warning("Stopped afkmover")
        elif re.match('!addquote', msg, re.I):
            if len(msg) > len("!addQuote "):
                Quotes.add(msg[len("!addQuote "):])
                Bot.send_msg_to_client(self.ts3conn, sender, "Quote '" + msg[len("!addQuote "):] + "' was added.")
        else:
            Bot.send_msg_to_client(self.ts3conn, sender, "I cannot interpret your command. I am very sorry. :(")
            logger.info("Unknown command " + msg + " received!")

    def multi_move(self, msg, sender=0):
        channels = msg[len("!multimove "):].split()
        source_name = ""
        dest_name = ""
        source = None
        dest = None
        if len(channels) < 2:
            if sender != 0:
                Bot.send_msg_to_client(self.ts3conn, sender, "Usage: multimove source destination")
                return
        elif len(channels) > 2:
            channel_name_list = self.ts3conn.channel_name_list()
            for channel_name in channel_name_list:
                if msg[len("!multimove "):].startswith(channel_name):
                    source_name = channel_name
                    dest_name = msg[len("!multimove ") + len(source_name)+1:]
        else:
            source_name = channels[0]
            dest_name = channels[1]
        if source_name == "":
            Bot.send_msg_to_client(self.ts3conn, sender, "Source channel not found")
            return
        if dest_name == "":
            Bot.send_msg_to_client(self.ts3conn, sender, "Destination channel not found")
            return
        try:
            channel_candidates = self.ts3conn.channelfind_by_name(source_name)
            if len(channel_candidates) > 0:
                source = channel_candidates[0].get("cid", '-1')
            if source is None or source == "-1":
                Bot.send_msg_to_client(self.ts3conn, sender, "Source channel not found")
                return
        except TS3QueryException:
            Bot.send_msg_to_client(self.ts3conn, sender, "Source channel not found")
        try:
            channel_candidates = self.ts3conn.channelfind_by_name(dest_name)
            if len(channel_candidates) > 0:
                dest = channel_candidates[0].get("cid", '-1')
            if dest is None or dest == "-1":
                Bot.send_msg_to_client(self.ts3conn, sender, "Destination channel not found")
                return
        except TS3QueryException:
            Bot.send_msg_to_client(self.ts3conn, sender, "Destination channel not found")
        try:
            clientlist = self.ts3conn.clientlist()
            self.logger.info(str(clientlist))
            self.logger.info("Moving all from " + source + " to " + dest)
            clientlist = [client for client in clientlist if client.get("cid", '-1') == source]
            for client in clientlist:
                clid = client.get("clid", '-1')
                self.logger.info("Found client in channel: " + client.get("client_nickname", "") + " id = " + clid)
                self.ts3conn.clientmove(int(dest), int(clid))
        except TS3QueryException as e:
            Bot.send_msg_to_client(self.ts3conn, sender, "Error moving clients: id = " +
                                   str(e.id) + e.message)

    def inform(self, event):
        if type(event) is Events.TextMessageEvent:
            if event.targetmode == "Private":
                if event.invoker_id != int(self.ts3conn.whoami()["client_id"]):  # Don't talk to yourself ...
                    ci = ClientInfo.ClientInfo(event.invoker_id, self.ts3conn)
                    self.logger.info("Message: " + event.message + " from: " + ci.name)
                    if ci.is_in_servergroups("Server Admin"):
                        self.handle_command(event.message, sender=event.invoker_id)
                    else:
                        Bot.send_msg_to_client(self.ts3conn, event.invoker_id, "Sorry, but I will only talk to admins!")
