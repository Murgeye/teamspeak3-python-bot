__author__ = 'Daniel'
import logging
import sys
import traceback

class TS3Event(object):
    def __init__(self, data):
        self._data = list(data)
        self._logger = logging.getLogger(__name__)
        self._logger.setLevel(logging.DEBUG)
        # create console handler and set level to debug
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)

    @property
    def data(self):
        return self._data


class EventParser(object):
    @staticmethod
    def parse_event(event, event_type):
        """
        :param event: dictionary
        :return:
        """
        # data = event.data[0].decode(encoding='UTF-8').split(" ")
        if "notifytextmessage" == event_type:
            parsed_event = TextMessageEvent(event)
            return parsed_event
        elif "notifyclientmoved" == event_type:
            if 'invokerid' in event:
                parsed_event = ClientMovedEvent(event)
            else:
                parsed_event = ClientMovedSelfEvent(event)
            return parsed_event
        elif "notifycliententerview" == event_type:
            parsed_event = ClientEnteredEvent(event)
            return parsed_event
        elif "notifyclientleftview" == event_type:
            parsed_event = ClientLeftEvent(event)
            return parsed_event
        elif "notifychanneldescriptionchanged" in event:
            parsed_event = ChannelDescriptionEditedEvent(event)
            return parsed_event
        elif "notifychanneledited" == event_type:
            parsed_event = ChannelEditedEvent(event)
            return parsed_event
        elif "serveredited" == event_type:
            parsed_event = ServerEditedEvent(event)
            return parsed_event
        else:
            logging.warning("Unknown event! " + str(event_type))
            return None


class ServerEditedEvent(TS3Event):
    def __init__(self, data):
        self._data = list(data)
        self._reason_id = data.get("reasonid", "")
        del data["reasonid"]
        self._invoker_id = data.get("invokerid", "-1")
        del data["invokerid"]
        self._invoker_uid = data.get("invokeruid", "-1")
        del data["invokeruid"]
        self._invoker_name = data.get("invokername", "")
        del data["invokername"]
        self._changed_properties = data

    @property
    def invoker_id(self):
        return self._invoker_id

    @property
    def invoker_name(self):
        return self._invoker_name

    @property
    def invoker_uid(self):
        return self._invoker_uid

    @property
    def reason_id(self):
        return self._reason_id

    @property
    def changed_properties(self):
        return self._changed_properties


class ChannelEditedEvent(TS3Event):
    def __init__(self, data):
        self._data = list(data)
        self._channel_id = data.get('cid', '-1')
        self._channel_topic = data.get('channel_topic', '')
        self._invoker_id = data.get('invokerid', '-1')
        self._invoker_name = data.get('invokername', '')
        self._invoker_uid = data.get('invokeruid', '-1')
        self._reason_id = data.get('reasonid', '-1')

    @property
    def channel_id(self):
        return self._channel_id

    @property
    def channel_topic(self):
        return self._channel_topic

    @property
    def invoker_id(self):
        return self._invoker_id

    @property
    def invoker_name(self):
        return self._invoker_name

    @property
    def invoker_uid(self):
        return self._invoker_uid

    @property
    def reason_id(self):
        return self._reason_id


class ChannelDescriptionEditedEvent(TS3Event):
    def __init__(self, data):
        self._data = list(data)
        self._channel_id = int(data.get('cid', '-1'))

    @property
    def channel_id(self):
        return self._channel_id


class ClientEnteredEvent(TS3Event):
    def __init__(self, data):
        self._data = list(data)
        try:
            self._client_id = int(data.get('clid', '-1'))
            self._client_name = data.get('client_nickname', '')
            self._client_uid = data.get('client_unique_identifier', '')
            self._client_description = data.get('client_description', '')
            self._client_country = data.get('client_country', '')
            self._client_away = data.get('client_away', '')
            self._client_away_msg = data.get('client_away_message', '')
            self._client_input_muted = data.get('client_input_muted', '')
            self._client_output_muted = data.get('client_output_muted', '')
            self._client_outputonly_muted = data.get('client_outputonly_muted', '')
            self._client_input_hardware = data.get('client_input_hardware', '')
            self._client_output_hardware = data.get('client_output_hardware', '')
            self._target_channel_id = int(data.get('ctid', '-1'))
            self._from_channel_id = int(data.get('cfid', '-1'))
            self._reason_id = int(data.get('reasonid', '-1'))
            self._client_is_recording = data.get('client_is_recording', '')
            self._client_dbid = data.get('client_database_id', '')
            self._client_servergroups = data.get('client_servergroups', '')
        except:
            self._logger.error("Failed to parse ClientEnterEvent:")
            self._logger.error(data)
            self._logger.error("\n\n")
            self._logger.error("Uncaught exception:" + str(sys.exc_info()[0]))
            self._logger.error(str(sys.exc_info()[1]))
            self._logger.error(traceback.format_exc())

    @property
    def client_id(self):
        return self._client_id

    @property
    def client_name(self):
        return self._client_name

    @property
    def client_uid(self):
        return self._client_uid

    @property
    def client_description(self):
        return self._client_description

    @property
    def client_country(self):
        return self._client_country

    @property
    def client_away(self):
        return self._client_away

    @property
    def client_away_msg(self):
        return self._client_away_msg

    @property
    def client_input_muted(self):
        return self._client_input_muted

    @property
    def client_output_muted(self):
        return self._client_output_muted

    @property
    def client_outputonly_muted(self):
        return self._client_outputonly_muted

    @property
    def client_input_hardware(self):
        return self._client_input_hardware

    @property
    def client_output_hardware(self):
        return self._client_output_hardware

    @property
    def target_channel_id(self):
        return self._target_channel_id

    @property
    def from_channel_id(self):
        return self._from_channel_id

    @property
    def reason_id(self):
        return self._reason_id

    @property
    def client_is_recording(self):
        return self._client_is_recording

    @property
    def client_dbid(self):
        return self._client_dbid

    @property
    def client_servergroups(self):
        return self._client_servergroups


class ClientLeftEvent(TS3Event):
    def __init__(self, data):
        self._data = list(data)
        self._client_id = int(data.get('clid', ''))
        self._target_channel_id = int(data.get('ctid', ''))
        self._from_channel_id = int(data.get('cfid', ''))
        self._reason_id = int(data.get('reasonid', ''))
        self._reason_msg = data.get('reasonmsg', '')

    @property
    def client_id(self):
        return self._client_id

    @property
    def target_channel_id(self):
        return self._target_channel_id

    @property
    def reason_id(self):
        return self._reason_id

    @property
    def reason_msg(self):
        return self._reason_msg


class ClientMovedEvent(TS3Event):
    def __init__(self, data):
        self._data = list(data)
        self._client_id = int(data.get('clid', '-1'))
        self._target_channel_id = int(data.get('ctid', '-1'))
        self._reason_id = int(data.get('reasonid', '-1'))
        self._invoker_id = int(data.get('invokerid', '-1'))
        self._invoker_name = data.get('invokername', '')
        self._invoker_uid = data.get('invokeruid', '')

    @property
    def client_id(self):
        return self._client_id

    @property
    def target_channel_id(self):
        return self._target_channel_id

    @property
    def reason_id(self):
        return self._reason_id

    @property
    def invoker_id(self):
        return self._invoker_id

    @property
    def invoker_name(self):
        return self._invoker_name

    @property
    def invoker_uid(self):
        return self._invoker_uid


class ClientMovedSelfEvent(TS3Event):
    def __init__(self, data):
        self._data = list(data)
        self._client_id = int(data.get('clid', '-1'))
        self._target_channel_id = int(data.get('ctid', '-1'))
        self._reason_id = int(data.get('reasonid', '-1'))

    @property
    def client_id(self):
        return self._client_id

    @property
    def target_channel_id(self):
        return self._target_channel_id

    @property
    def reason_id(self):
        return self._reason_id


class TextMessageEvent(TS3Event):
    def __init__(self, data):
        self._data = list(data)
        if data.get('targetmode') is '1':
            self._targetmode = 'Private'
            self._target = data.get('target')
        elif data.get('targetmode') is '2':
            self._targetmode = 'Channel'
        elif data.get('targetmode') is '3':
            self._targetmode = 'Server'

        self._message = data.get('msg')
        self._invoker_id = int(data.get('invokerid', '-1'))
        self._invoker_name = data.get('invokername', '')
        self._invoker_uid = data.get('invokeruid', '-1')

    @property
    def invoker_id(self):
        return self._invoker_id

    @property
    def invoker_name(self):
        return self._invoker_name

    @property
    def invoker_uid(self):
        return self._invoker_uid

    @property
    def message(self):
        return self._message

    @property
    def targetmode(self):
        return self._targetmode

    @property
    def target(self):
        if self.get_targetmode() is 'Private':
            return self._target
        else:
            return None
