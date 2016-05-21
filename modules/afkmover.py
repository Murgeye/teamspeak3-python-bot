__author__ = 'Fabian'
from threading import Thread
import logging
import sys
import traceback
from Moduleloader import *
import ts3.Events as Events
import threading
import ts3
afkMover = None
afkStopper = threading.Event()
bot = None
autoStart = True

@command('startafk','afkmove',)
def start_afkmover(sender=None, msg=None):
    global afkMover
    if afkMover is None:
        afkMover = AfkMover(afkStopper, bot.ts3conn)
        afkStopper.clear()
        afkMover.start()

@command('stopafk','afkstop')
def stop_afkmover(sender, msg):
    global afkMover
    afkStopper.set()
    afkMover = None

@event(Events.ClientLeftEvent,)
def client_left(event):
    # Forgets clients that were set to afk and then left
    if afkMover is not None:
        if str(event.client_id) in afkMover.client_channels:
            del afkMover.client_channels[str(event.client_id)]

@setup
def setup(ts3Bot):
    global bot
    bot = ts3Bot
    if autoStart:
        start_afkmover()


@exit
def exit():
    global afkMover
    afkStopper.set()
    afkMover.join()
    afkMover = None

class AfkMover(Thread):
    logger = logging.getLogger("afk")
    logger.setLevel(logging.WARNING)
    file_handler = logging.FileHandler("afk.log", mode='a+')
    formatter = logging.Formatter('AFK Logger %(asctime)s %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.info("Configured afk logger")
    logger.propagate = 0

    def __init__(self, event, ts3conn):
        Thread.__init__(self)
        self.stopped = event
        self.ts3conn = ts3conn
        self.afk_channel = self.get_afk_channel()
        self.client_channels = {}
        self.afk_list = None
        if self.afk_channel is None:
            AfkMover.logger.error("Could not get afk channel")

    def run(self):
        AfkMover.logger.info("AFKMove Thread started")
        self.auto_move_all()

    def update_afk_list(self):
        try:
            self.afk_list = self.ts3conn.clientlist(["away"])
            AfkMover.logger.debug("Awaylist: " + str(self.afk_list))
        except ts3.TS3Exception:
            AfkMover.logger.exception("Error getting away list!")
            self.afk_list = list()

    def get_away_list(self):
        if self.afk_list is not None:
            AfkMover.logger.debug(str(self.afk_list))
            awaylist = list()
            for client in self.afk_list:
                AfkMover.logger.debug(str(self.afk_list))
                if "cid" not in client.keys():
                    AfkMover.logger.error("Client without cid!")
                    AfkMover.logger.error(str(client))
                elif "client_away" in client.keys() and client.get("client_away", '0') == '1' and int(client.get("cid", '-1')) != \
                        int(self.afk_channel):
                    awaylist.append(client)
            return awaylist
        else:
            AfkMover.logger.error("Clientlist is None!")
            return list()

    def get_back_list(self):
        clientlist = [client for client in self.afk_list if client.get("client_away", '1') == '0' and int(client.get("cid",
                                                                                                                  '-1'))
                      == int(self.afk_channel)]
        return clientlist

    def get_afk_channel(self, name="AFK"):
        try:
            channel = self.ts3conn.channelfind(name)[0].get("cid", '-1')
        except ts3.TS3Exception:
            AfkMover.logger.exception("Error getting afk channel")
            raise
        return channel

    def move_to_afk(self, clients):
        AfkMover.logger.info("Moving clients to afk!")
        for client in clients:
            AfkMover.logger.info("Moving somebody to afk!")
            AfkMover.logger.debug("Client: " + str(client))
            try:
                self.ts3conn.clientmove(self.afk_channel, int(client.get("clid", '-1')))
            except ts3.TS3Exception:
                AfkMover.logger.exception("Error moving client! Clid=" + str(client.get("clid", '-1')))
            self.client_channels[client.get("clid", '-1')] = client.get("cid", '0')
            AfkMover.logger.debug("Moved List after move: " + str(self.client_channels))

    def move_all_afk(self):
        try:
            afk_list = self.get_away_list()
            self.move_to_afk(afk_list)
        except AttributeError:
            AfkMover.logger.exception("Connection error!")

    def move_all_back(self):
        back_list = self.get_back_list()
        AfkMover.logger.debug("Moving clients back")
        AfkMover.logger.debug("Backlist is: " + str(back_list))
        AfkMover.logger.debug("Saved channel list keys are:" + str(self.client_channels.keys()) + "\n")
        for client in back_list:
            if client.get("clid", -1) in self.client_channels.keys():
                AfkMover.logger.info("Moving a client back!")
                AfkMover.logger.debug("Client: " + str(client))
                AfkMover.logger.debug("Saved channel list keys:" + str(self.client_channels))
                self.ts3conn.clientmove(self.client_channels.get(client.get("clid", -1)), int(client.get("clid", '-1')))
                del self.client_channels[client.get("clid", '-1')]

    def auto_move_all(self):
        while not self.stopped.wait(2.0):
            AfkMover.logger.debug("Afkmover running!")
            self.update_afk_list()
            try:
                self.move_all_back()
                self.move_all_afk()
            except:
                AfkMover.logger.error("Uncaught exception:" + str(sys.exc_info()[0]))
                AfkMover.logger.error(str(sys.exc_info()[1]))
                AfkMover.logger.error(traceback.format_exc())
                AfkMover.logger.error("Saved channel list keys are:" + str(self.client_channels.keys()) + "\n")
        AfkMover.logger.warning("AFKMover stopped!")
        self.client_channels = {}
