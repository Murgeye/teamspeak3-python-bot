# standard imports
import configparser
import logging
import sys
from distutils.util import strtobool

# third-party imports
import ts3API.TS3Connection
from ts3API.TS3Connection import TS3QueryException
from ts3API.TS3QueryExceptionType import TS3QueryExceptionType

# local imports
import command_handler
import event_handler
import module_loader


def stop_conn(ts3conn):
    """Stops the connection."""
    ts3conn.stop_recv.set()


def send_msg_to_client(ts3conn, clid, msg):
    """
    Convenience method for sending a message to a client without having a bot object.
    :param ts3conn: TS3Connection to send message on.
    :type ts3conn: ts3API.TS3Connection
    :param clid: Client id of the client to send too.
    :type clid: int
    :param msg: Message to send
    :type msg: str
    :return:
    """
    try:
        ts3conn.sendtextmessage(targetmode=1, target=clid, msg=msg)
    except ts3API.TS3Connection.TS3QueryException:
        logger = logging.getLogger("bot")
        logger.exception("Error sending a message to clid %s", int(clid))


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
    def bot_from_config(config):
        """
        Create a bot from the values parsed from config.ini
        :param config: a configuration for the bot
        :type config: dict
        :return: Created Bot
        :rtype: Ts3Bot
        """
        logger = logging.getLogger("bot")
        plugins = config
        config = config.pop("General")
        return Ts3Bot(logger=logger, plugins=plugins, **config)

    @staticmethod
    def parse_config(logger):
        """
        Parse the config file config.ini
        :param logger: Logger to log errors to.
        :return: Dictionary containing options necessary to create a new bot
        :rtype: dict[str, dict[str, str]]
        """
        config = configparser.ConfigParser()
        if len(config.read("config.ini")) == 0:
            logger.error("Config file missing!")
            sys.exit(1)
        if not config.has_section("General"):
            logger.error("Config file is missing general section!")
            sys.exit(1)
        if not config.has_section("Plugins"):
            logger.error("Config file is missing plugins section")
            sys.exit(1)
        return config._sections

    def connect(self):
        """
        Connect to the server specified by self.host and self.port.
        :return:
        """
        try:
            self.ts3conn = ts3API.TS3Connection.TS3Connection(
                self.host,
                self.port,
                use_ssh=self.is_ssh,
                username=self.user,
                password=self.password,
                accept_all_keys=self.accept_all_keys,
                host_key_file=self.host_key_file,
                use_system_hosts=self.use_system_hosts,
                sshtimeout=self.sshtimeout,
                sshtimeoutlimit=self.sshtimeoutlimit,
            )
            # self.ts3conn.login(self.user, self.password)
        except ts3API.TS3Connection.TS3QueryException:
            self.logger.exception(
                "Error while connecting, IP propably not whitelisted or Login data wrong!"
            )
            raise

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
        except ts3API.TS3Connection.TS3QueryException:
            self.logger.exception("Error on use SID")
            sys.exit(1)
        try:
            try:
                self.ts3conn.clientupdate(["client_nickname=" + self.bot_name])
            except TS3QueryException as query_exception:
                if query_exception.type == TS3QueryExceptionType.CLIENT_NICKNAME_INUSE:
                    self.logger.info(
                        "The choosen bot nickname is already in use, keeping the default nickname"
                    )
                else:
                    raise query_exception
            try:
                self.channel = self.get_channel_id(self.default_channel)
                self.ts3conn.clientmove(
                    self.channel, int(self.ts3conn.whoami()["client_id"])
                )
            except TS3QueryException as query_exception:
                if query_exception.type == TS3QueryExceptionType.CHANNEL_ALREADY_IN:
                    self.logger.info(
                        "The bot is already in the configured default channel"
                    )
                else:
                    raise query_exception
        except TS3QueryException:
            self.logger.exception("Error on setting up client")
            self.ts3conn.quit()
            return
        self.command_handler = command_handler.CommandHandler(self.ts3conn)
        self.event_handler = event_handler.EventHandler(
            ts3conn=self.ts3conn, command_handler=self.command_handler
        )
        try:
            self.ts3conn.register_for_server_events(self.event_handler.on_event)
            self.ts3conn.register_for_channel_events(0, self.event_handler.on_event)
            self.ts3conn.register_for_private_messages(self.event_handler.on_event)
        except ts3API.TS3Connection.TS3QueryException:
            self.logger.exception("Error on registering for events.")
            sys.exit(1)

    def __del__(self):
        if self.ts3conn is not None:
            self.ts3conn.quit()

    def __init__(
        self,
        host,
        port,
        serverid,
        user,
        password,
        defaultchannel,
        botname,
        logger,
        plugins,
        ssh="False",
        acceptallsshkeys="False",
        sshhostkeyfile=None,
        sshloadsystemhostkeys="False",
        sshtimeout=None,
        sshtimeoutlimit=3,
        *_,
        **__,
    ):
        """
        Create a new Ts3Bot.
        :param host: Host to connect to, can be a IP or a host name
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
        self.sid = serverid
        self.default_channel = defaultchannel
        self.bot_name = botname
        self.event_handler = None
        self.command_handler = None
        self.channel = None
        self.logger = logger
        self.ts3conn = None
        self.is_ssh = bool(strtobool(ssh))
        # Strtobool returns 1/0 ...
        self.accept_all_keys = bool(strtobool(acceptallsshkeys))
        self.host_key_file = sshhostkeyfile
        self.use_system_hosts = bool(strtobool(sshloadsystemhostkeys))
        self.sshtimeout = sshtimeout
        self.sshtimeoutlimit = sshtimeoutlimit

        self.connect()
        self.setup_bot()
        # Load modules
        module_loader.load_modules(self, plugins)
        self.ts3conn.start_keepalive_loop()
