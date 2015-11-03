__author__ = 'fabian'
import telnetlib
import socket
import logging
import threading
import time
import ts3.Events as Events
import blinker
import ts3.utilities


class TS3Connection(object):
    """
    Connection class for the TS3 API. Uses a telnet connection to send messages to and receive messages from the
    Teamspeak 3 server.
    """
    def __init__(self, host="127.0.0.1", port=10011):
        """
        Creates a new TS3Connection.
        :param host: Host to connect to. Can be an IP address or a hostname.
        :param port: Port to connect to.
        :type host: str
        :type port: int
        """
        self._tel_lock = threading.Lock()
        self._tel_conn = telnetlib.Telnet(host, port, timeout=socket.getdefaulttimeout())
        self._logger = logging.getLogger(__name__)
        self._logger.setLevel(logging.WARNING)
        self.stop_recv = threading.Event()
        self._new_data = threading.Event()
        self._data_read = threading.Event()
        self._data_read.set()
        self._data = None
        # create console handler and set level to warning
        file_handler = logging.FileHandler("api.log", mode='a+')
        file_handler.setLevel(logging.WARNING)

        # create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # add formatter to ch
        file_handler.setFormatter(formatter)

        # add ch to logger
        self._logger.addHandler(file_handler)
        self._logger.debug(self._tel_conn.read_until(b"\n\r"))
        self._logger.debug(self._tel_conn.read_until(b"\n\r"))
        threading.Thread(target=self._recv).start()

    def login(self, user, password):
        """
        Login with query credentials.
        :param user: Username to login with.
        :param password: Password to login with.
        :type user: str
        :type password: str
        """
        self._send("login", [user, password])

    def use(self, sid):
        """
        Chose the virtual server to use.
        :param sid: SID of the virtual server to use.
        :type sid: int
        """
        self._send("use", [str(sid)])

    def clientlist(self, params=None):
        """
        Get a clientlist from the server.
        :param params: List of parameters strings to use.
        :type params: list[str]
        :return:
        """
        if params is None:
            params = []
        args = list()
        for p in params:
            args.append("-" + p)
        clist = self._send("clientlist", args)
        clients = TS3Connection._parse_resp_to_list_of_dicts(clist)
        if len(clients)==0:
            self._logger.warning("Clientlist empty" +str(clist))
        return clients

    def _send(self, command, args=list(), wait_for_resp=True, log_keepalive=False):
        """
        :param command: Command to send.
        :param args: Parameter to send, will be escaped.
        :param wait_for_resp: True: Expects at least a error line and blocks until one is received. False:
                Almost exclusively for keepalive, doesn't wait for an acknowledgment.
        :param log_keepalive: Should keepalive messages be logged?
        :return: Query response, if one was received.
        :rtype: bytes | None
        :type command: str
        :type args: list[str]
        :type wait_for_resp: bool
        :type log_keepalive: bool
        """
        query = command
        saved_resp = b''
        ack = False
        for arg in args:
            query += " " + ts3.utilities.escape(arg)
        query += "\n\r"
        query = query.encode()
        resp = None
        if self._tel_lock.acquire():
            if not query == b'\n\r' or query == b'\n\r' and log_keepalive:
                self._logger.debug("Query: " + str(query))
            self._tel_conn.write(query)
            if not wait_for_resp:
                self._tel_lock.release()
                return
            while not ack:
                while resp is None:
                    self._new_data.wait()
                    resp = self._data
                    self._new_data.clear()
                    self._data_read.set()
                    if resp is not None:
                        if resp[0] == b'error':
                            ack = True
                            if resp[1] != b'id=0':
                                self._tel_lock.release()
                                raise TS3QueryException(int(resp[1].decode(encoding='UTF-8').split("=", 1)[1]), resp[2].
                                                        decode(encoding='UTF-8'))
                        else:
                            self._logger.debug("Resp: " + str(resp))
                            saved_resp += resp
                            resp = None
        self._tel_lock.release()
        self._logger.debug("Saved resp:" + str(saved_resp))
        return saved_resp

    def _recv(self):
        """
        Actual receiving, receives until \n\r is encountered. \n\r is cut from the end of the response.
        :return: Parsed response, split by " " or None if received message was an event.
        :rtype: bytes | None
        """
        while not self.stop_recv.is_set():
            try:
                resp = self._tel_conn.read_until(b"\n\r")[:-2]
            except EOFError:
                if self.stop_recv.is_set():
                    self._tel_conn.close()
                    return
                else:
                    raise TS3Exception("Connection was closed!")
            self._logger.debug("Response: " + str(resp))
            data = self._parse_resp(resp)
            self._logger.debug("Data: " + str(data))
            if data is not None:
                self._data_read.wait()
                self._data = data
                self._data_read.clear()
                self._new_data.set()

    @staticmethod
    def _parse_resp_to_dict(resp):
        """
        Splits a response by " " and saves it in a dictionary.
        :type resp: bytes
        :param resp: Message to parse.
        :return: Dictionary containing all info extracted from the response.
        :rtype: dict[str, str]
        """
        resp = resp.decode(encoding='UTF-8').split(" ")
        info = dict()
        for part in resp:
            split = part.split('=', 1)
            # TODO: Handle empty data?
            if len(split) == 2:
                key, value = split
                info[key] = ts3.utilities.unescape(value)
        return info

    @staticmethod
    def _parse_resp_to_list_of_dicts(resp):
        """
        Parses multiple elements in a message into a list of dictionaries containing the info for each element.
        :type resp: bytes
        :param resp: Message to parse.
        :return: List of dictionaries containing the info.
        :rtype: list[dict[str, str]]
        """
        # Multiple responses are split by "|"
        split_list = resp.split(b"|")
        dict_list = list()
        for resp in split_list:
            if len(resp) > 0:
                dict_list.append(TS3Connection._parse_resp_to_dict(resp))
        return dict_list

    def register_for_private_messages(self, event_listener=None):
        """
        Register the event_listener for private message events. Be careful, you should ignore your own messages by
        comparing the invoker_id to your client id ...
        :param event_listener: Blinker signal handler function to be informed: on_event(sender, **kw), kw will contain
        the event
        :type event_listener: (str, dict[str, any]) -> None
        """
        self._send("servernotifyregister", ["event=textprivate"])
        if event_listener is not None:
            blinker.signal("event").connect(event_listener)

    def register_for_server_events(self, event_listener=None):
        """
        Register event_listener for receiving server_events.
        :param event_listener: Blinker signal handler function to be informed: on_event(sender, **kw), kw will contain
        the event
        :type event_listener: (str, dict[str, any]) -> None
        """
        self._send("servernotifyregister", ["event=server"])
        if event_listener is not None:
            blinker.signal("event").connect(event_listener)

    def clientmove(self, channel_id, client_id):
        """
        Move a client to another channel.
        :param channel_id: Channel to move client to.
        :param client_id: Id of the client to move.
        :type channel_id: int
        :type client_id: int
        """
        self._send("clientmove", ["cid="+str(channel_id), "clid="+str(client_id)])

    def clientupdate(self, params=None):
        """
        Update the query clients data.
        :param params: List of parameters to update in the form param=value.
        :type params: list[str]
        """
        if params is None:
            params = []
        self._send("clientupdate", params)

    def whoami(self):
        """
        Returns info of the query client.
        :return: Dictionary of query client information.
        :rtype: dict[str, str]
        """
        who = TS3Connection._parse_resp_to_dict(self._send("whoami", []))
        self._logger.info("Whoami: " + str(who))
        return who

    def channellist(self, params=None):
        if params is None:
            params = []
        args = list()
        for p in params:
            args.append("-" + p)
        channel_list = self._send("channellist", args)
        channels = TS3Connection._parse_resp_to_list_of_dicts(channel_list)
        if len(channels) == 0:
            self._logger.warning("Channellist empty" + str(channel_list))
        return channels

    def channel_name_list(self):
        names = list()
        channels = self.channellist()
        for channel in channels:
            names.append(channel.get("channel_name", ""))
        return names

    def channelfind(self, pattern):
        """
        Returns all channels with a name corresponding to pattern.
        :param pattern: Pattern to look for.
        :return: List of channels.
        :rtype: list[dict[str, str]]
        """
        return TS3Connection._parse_resp_to_list_of_dicts(self._send("channelfind", ["pattern="+pattern]))

    def channelfind_by_name(self, name):
        """
        Returns all channels with a name that is exactly the same as the given name.
        :param name: Name to look for.
        :return: List of channels
        :rtype: list[dict[str, str]]
        """
        channel_candidates = self.channelfind(name)
        channel_list = list()
        for candidate in channel_candidates:
            if candidate.get("channel_name", "") == name:
                channel_list.append(candidate)
        return channel_list

    def sendtextmessage(self, targetmode, target, msg):
        """
        Sends a textmessage to the specified target.
        :param targetmode: 1: private message 2: textchannel 3: servertext
        :param target: client_id/channel_id
        :param msg: Message to send.
        :type targetmode: int
        :type target: int
        :type msg: str
        """
        self._send("sendtextmessage", ["targetmode="+str(targetmode), "target="+str(target), "msg="+str(msg)])

    def servergrouplist(self):
        """
        Returns a list of all servergroups with corresponding info.
        :return: List of servergroups.
        :rtype: list[dict[str, str]]
        """
        return TS3Connection._parse_resp_to_list_of_dicts(self._send("servergrouplist"))

    def clientinfo(self, client_id):
        """
        Returns clientinfo for a client specified by its id.
        :param client_id: Id of the client.
        :return: Dictionary of client information.
        :rtype: dict[str,str]
        """
        return self._parse_resp_to_dict(self._send("clientinfo", ["clid="+str(client_id)]))

    def _parse_resp(self, resp):
        """
        Parses a response. Messages starting with notify... are handled as events and the listeners connected are
        informed. Messages starting with error are split by " " and returned, all other messages will just be returned
         and can be handled by the caller.
        :param resp: Message to parse.
        :type resp: byte
        :return: None if message notifies of an event, dictionary containing id and message on acknowledgements and
        bytes on any other message.
        :rtype: None | dict[str, str] | bytes
        """
        # Acknowledgements
        if resp.startswith(b'error'):
            resp = resp.split(b' ')
            return resp
        # Events
        elif resp.startswith(b'notify'):
            resp = resp.decode(encoding='UTF-8').split(" ")
            event_type = resp[0]
            event = dict()
            for info in resp[1:]:
                split = info.split('=', 1)
                if len(split) == 2:
                    key, value = split
                    event[key] = ts3.utilities.unescape(value)
            event = Events.EventParser.parse_event(event, event_type)
            signal = blinker.signal("event")
            self._logger.debug("Sending signal")
            threading.Thread(target=signal.send, kwargs={'event': event}).start()
            return None
        # Query-Responses and other things(What could these be?)
        else:
            return resp

    def _recv_wait_timeout(self, timeout=0.1):
        """
        Like receives, but only reads for timeout seconds. If no info is received, the function returns, otherwise
        it reads a whole line before returning. This is used for receiving notify messages.
        :param timeout: Seconds to wait before returning if no message was received.
        :return: None if nothing was received, parsed response corresponding to _parse_resp otherwise.
        :rtype: None | dict[str, str] | bytes
        """
        resp = self._tel_conn.read_until(b"\n\r", timeout)
        if len(resp) > 0 and not resp.endswith(b"\n\r"):
            resp += self._tel_conn.read_until(b"\n\r")[:-2]
        if len(resp) > 0:
            self._logger.debug("No wait Response: " + str(resp))
            return self._parse_resp(resp)

    def _send_keepalive(self):
        """
        Sends a keepalive message to the server to prevent timeout. Keepalive message is "\n\r".
        """
        self._send("", wait_for_resp=False)

    def keepalive_loop(self, interval=5):
        """
        Sends keepalive messages every interval seconds and checks for new messages. Runs until self.stop_recv is set.
        :param interval: Seconds to wait between keepalive messages.
        :type interval: int
        """
        while not self.stop_recv.wait(interval):
            self._send_keepalive()
            time.sleep(interval)

    def quit(self):
        """
        Stops the connection from receiving and sends the quit signal.
        """
        # Avoid unclean exit by interfering with response to pending query
        if self._tel_lock.acquire():
            self.stop_recv.set()
        self._tel_lock.release()
        self._send("quit")

    def start_keepalive_loop(self, interval=5):
        """
        Starts a thread that sends keepalive messages every interval seconds.
        :param interval: Seconds between to keepalive messages.
        :return:
        """
        threading.Thread(target=self.keepalive_loop, args=(interval,)).start()


class TS3Exception(Exception):
    pass


class TS3QueryException(TS3Exception):
    def __init__(self, error_id, message):
        """
        Creates a new QueryException.
        :param error_id: Id of the error.
        :param message: Error message.
        :type error_id: int
        :type message: str
        """
        self._id = error_id
        self._msg = ts3.utilities.unescape(message)
        super(TS3Exception, self).__init__("Query failed with id = "+str(error_id))

    @property
    def message(self):
        return self._msg

    @property
    def id(self):
        return self._id
