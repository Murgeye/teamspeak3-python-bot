# standard imports
import logging
import re

logger = logging.getLogger("bot")


class ClientInfo:
    """
    ClientInfo contains various attributes of the client with the given client id
    The attributes in this object have been filtered, if you want to know about all
    possible attributes, use print(client_data[0].keys())
    """

    def __init__(self, client_id, ts3conn):
        if client_id == "-1":
            logger.error("Trying to get ClientInfo of clid=-1")
            logger.warning("Giving out mock object ...")
            client_data = [{}]
        else:
            client_data = ts3conn.clientinfo(client_id)
        self._name = client_data.get("client_nickname", "")
        self._unique_id = client_data.get("client_unique_identifier", "")
        self._database_id = client_data.get("client_database_id", "")
        # servergroups is a list of strings
        sgs = {}
        for servergroup in ts3conn.servergrouplist():
            sgs[servergroup.get("sgid")] = servergroup.get("name")
        servergroups_list = client_data.get("client_servergroups", "").split(",")
        self._servergroups = []
        for servergroup in servergroups_list:
            group = sgs.get(servergroup)
            if group is not None:
                self._servergroups.append(group)
        self._description = client_data.get("client_description", "")
        self._country = client_data.get("client_country", "")
        self._created = client_data.get("client_created", "")
        self._total_connections = client_data.get("client_totalconnections", "")
        self._last_connection = client_data.get("client_lastconnected", "")
        self._connected_time = client_data.get("connection_connected_time", "")
        self._platform = client_data.get("client_platform", "")
        self._version = client_data.get("client_version", "")
        self._ip = client_data.get("connection_client_ip", "")
        self._away = client_data.get("client_away", "")
        self._idle_time = client_data.get("client_idle_time", "")
        self._input_muted = client_data.get("client_input_muted", "")
        self._output_muted = client_data.get("client_output_muted", "")
        self._outputonly_muted = client_data.get("client_outputonly_muted", "")
        self._input_hardware = client_data.get("client_input_hardware", "")
        self._output_hardware = client_data.get("client_output_hardware", "")
        self._channel_id = client_data.get("cid", "-1")
        if len(servergroups_list) == 0:
            logger.error("Client without servergroups parsed ...")
            logger.error(
                "IP: %s, Name: %s, channel_id: %s", self.ip, self.name, self.channel_id
            )
            logger.error(str(client_data))

    @property
    def channel_id(self):
        """Return channel ID"""
        return self._channel_id

    @property
    # pylint: disable=invalid-name
    def ip(self):
        """Return IP address"""
        return self._ip

    @property
    def name(self):
        """Return name"""
        return self._name

    @property
    def servergroups(self):
        """Return servergroups"""
        return self._servergroups

    def is_in_servergroups(self, pattern):
        """Checks, whether the client is member of the specific group or not."""
        for servergroup in self._servergroups:
            if re.search(pattern=pattern, string=servergroup) is not None:
                return True
        return False

    def __getattr__(self, item):
        return self.__getattribute__(f"_{item}")
