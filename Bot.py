import ts3.TS3Connection
import EventHandler
import logging
import textcommands
import Moduleloader
import configparser


def stop_conn(ts3conn):
    ts3conn.stop_recv.set()


def send_msg_to_client(ts3conn, clid, msg):
    """
    Convenience method for sending a message to a client without having a bot object.
    :param ts3conn: TS3Connection to send message on.
    :type ts3conn: ts3.TS3Connection
    :param clid: Client id of the client to send too.
    :type clid: int
    :param msg: Message to send
    :type msg: str
    :return:
    """
    try:
        ts3conn.sendtextmessage(targetmode=1, target=clid, msg=msg)
    except ts3.TS3Connection.TS3QueryException:
        logger = logging.getLogger("bot")
        logger.exception("Error sending a message to clid " + str(clid))


class Ts3Bot:
    """
    Teamspeak 3 Bot with module support.
    """
    def get_channel_id(self, name):
        """
        Covenience method for getting a channel by name.
        :param name: Channel name to search for, can be a pattern
        :type name: str
        :return: Channel id of the first channel found
        :rtype: int
        """
        ret = self.ts3conn.channelfind(pattern=name)
        return int(ret[0]["cid"])

    @staticmethod
    def bot_from_config():
        """
        Create a bot from the values parsed from config.ini
        :return: Created Bot
        :rtype: Ts3Bot
        """
        logger = logging.getLogger("bot")
        config = Ts3Bot.parse_config(logger)
        return Ts3Bot(logger=logger, **config)

    @staticmethod
    def parse_config(logger):
        """
        Parse the config file config.ini
        :param logger: Logger to log errors to.
        :return: Dictionary containing options necessary to create a new bot
        :rtype: dict[str, str]
        """
        config = configparser.ConfigParser()
        if len(config.read('config.ini')) == 0:
            logger.error("Config file missing!")
            exit()
        if not config.has_section('General'):
            logger.error("Config file is missing general section!")
            exit()
        config_dict = dict()
        try:
            config_dict['host'] = config.get('General', 'Host')
            config_dict['port'] = config.get('General', 'Port')
            config_dict['sid'] = config.get('General', 'ServerId')
            config_dict['user'] = config.get('General', 'User')
            config_dict['password'] = config.get('General', 'Password')
            config_dict['default_channel'] = config.get('General', 'DefaultChannel')
            config_dict['bot_name'] = config.get('General', 'BotName')
        except configparser.NoOptionError as e:
            logger.error("Config is missing an option.")
            logger.error(e.message)
            exit()
        return config_dict

    def connect(self):
        """
        Connect to the server specified by self.host and self.port.
        :return:
        """
        try:
            self.ts3conn = ts3.TS3Connection.TS3Connection(self.host, self.port)
            self.ts3conn.login(self.user, self.password)
        except ts3.TS3Connection.TS3QueryException:
            self.logger.error("Error while connecting, IP propably not whitelisted or Login data wrong!")
            exit()

    def setup_bot(self):
        """
        Setup routine for new bot. Does the following things:
            1. Select virtual server specified by self.sid
            2. Set bot nickname to the Name specified by self.bot_name
            3. Move the bot to the channel specified by self.default_channel
            4. Register command and event handlers
        :return:
        """
        try:
            self.ts3conn.use(sid=self.sid)
        except ts3.TS3Connection.TS3QueryException:
            self.logger.exception("Error on use SID")
            exit()
        try:
            self.channel = self.get_channel_id(self.default_channel)
            self.ts3conn.clientupdate(["client_nickname=" + self.bot_name])
            self.ts3conn.clientmove(self.channel, int(self.ts3conn.whoami()["client_id"]))
        except ts3.TS3Connection.TS3QueryException:
            self.logger.exception("Error on setting up client")
            self.ts3conn.quit()
            return
        self.command_handler = textcommands.CommandHandler(self.ts3conn)
        self.event_handler = EventHandler.EventHandler(ts3conn=self.ts3conn, command_handler=self.command_handler)
        try:
            self.ts3conn.register_for_server_events(self.event_handler.on_event)
            self.ts3conn.register_for_private_messages(self.event_handler.on_event)
        except ts3.TS3Connection.TS3QueryException:
            self.logger.exception("Error on registering for events.")
            exit()

    def __del__(self):
        if self.ts3conn is not None:
            self.ts3conn.quit()

    def __init__(self, host, port, sid, user, password, default_channel, bot_name, logger):
        """
        Create a new Ts3Bot.
        :param host: Host to connect to, can be a IP or a dns name
        :param port: Port to connect to
        :param sid: Virtual Server id to use
        :param user: Server Query Admin Login Name
        :param password: Server Query Admin Password
        :param default_channel: Channel to move the bot to
        :param bot_name: Nickname of the bot
        :param logger: Logger to use throughout the bot
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.sid = sid
        self.default_channel = default_channel
        self.bot_name = bot_name
        self.event_handler = None
        self.command_handler = None
        self.channel = None
        self.logger = logger
        self.ts3conn = None
        self.connect()
        self.setup_bot()
        # Load modules
        Moduleloader.load_modules(self)
        self.ts3conn.start_keepalive_loop()
