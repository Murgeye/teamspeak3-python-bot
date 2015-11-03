import ts3.TS3Connection
import EventHandler
import ts3.Events as Events
import logging
import textcommands
import Quotes
from __conn_settings__ import *


def stop_conn(ts3conn):
    ts3conn.stop_recv.set()


def send_msg_to_client(ts3conn, clid, msg):
    try:
        ts3conn.sendtextmessage(targetmode=1, target=clid, msg=msg)
    except ts3.TS3Connection.TS3QueryException:
        logger = logging.getLogger("bot")
        logger.exception("Error sending a message to clid " + str(clid))


class Ts3Bot:
    def get_channel_id(self, name):
        ret = self.ts3conn.channelfind(pattern=name)
        return int(ret[0]["cid"])

    def __del__(self):
        if self.event_handler is not None:
            self.event_handler.command_handler.afkStopper.set()
        self.ts3conn.quit()

    def __init__(self):
        self.event_handler = None
        self.logger = logging.getLogger("bot")
        try:
            self.ts3conn = ts3.TS3Connection.TS3Connection(HOST, PORT)
            self.ts3conn.login(USER, PASS)
        except ts3.TS3Connection.TS3QueryException:
            self.logger.error("Error while connecting, IP propably not whitelisted or Login data wrong!")
            exit()
        try:
            self.ts3conn.use(sid=SID)
        except ts3.TS3Connection.TS3QueryException:
            self.logger.exception("Error on use SID")
            exit()
        # self.ts3conn.keepalive()
        try:
            self.channel = self.get_channel_id(DEFAULTCHANNEL)
            self.ts3conn.clientupdate(["client_nickname="+BOTNAME])
            self.ts3conn.clientmove(self.channel, int(self.ts3conn.whoami()["client_id"]))
        except ts3.TS3Connection.TS3QueryException:
            self.logger.exception("Error on setting up client")
            self.ts3conn.quit()
            return
        self.command_handler = textcommands.CommandHandler(self.ts3conn)
        self.event_handler = EventHandler.EventHandler(ts3conn=self.ts3conn, command_handler=self.command_handler)
        # self.ts3conn.on_event.connect(self.event_handler.on_event)
        try:
            self.ts3conn.register_for_server_events(self.event_handler.on_event)
            # self.channellist = self.ts3conn.channellist()
            # self.ts3conn.servernotifyregister(event="channel", id_=0)
            # self.ts3conn.servernotifyregister(event="textserver")
            # self.ts3conn.servernotifyregister(event="textchannel")
            self.ts3conn.register_for_private_messages(self.event_handler.on_event)
        except ts3.TS3Connection.TS3QueryException:
            self.logger.exception("Error on registering for events.")
            exit()
        self.command_handler.start_afkmover()
        self.quoter = Quotes.Quoter(self.ts3conn)
        self.event_handler.add_observer(self.quoter, Events.ClientEnteredEvent)
        self.ts3conn.start_keepalive_loop()
        '''
        try:
            # self.ts3conn.recv_loop()
            # self.ts3conn.recv(recv_forever=True)
        except EOFError:
            self.logger.warning("Bot has ended!")
        '''