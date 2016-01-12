__author__ = 'Daniel'
import ts3.Events as Events
import logging
import threading


class EventHandler(object):
    logger = logging.getLogger("eventhandler")
    logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler("eventhandler.log", mode='a+')
    formatter = logging.Formatter('Eventhandler Logger %(asctime)s %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.info("Configured Eventhandler logger")
    logger.propagate = 0

    def __init__(self, ts3conn, command_handler):
        self.ts3conn = ts3conn
        self.command_handler = command_handler
        self.observers = {}
        self.add_observer(self.command_handler.inform, Events.TextMessageEvent)

    def on_event(self, sender, **kw):
        # parsed_event = Events.EventParser.parse_event(event=event)
        parsed_event = kw["event"]
        if type(parsed_event) is Events.TextMessageEvent:
            logging.debug(type(parsed_event))
        elif type(parsed_event) is Events.ChannelEditedEvent:
            logging.debug(type(parsed_event))
        elif type(parsed_event) is Events.ChannelDescriptionEditedEvent:
            logging.debug(type(parsed_event))
        elif type(parsed_event) is Events.ClientEnteredEvent:
            logging.debug(type(parsed_event))
        elif type(parsed_event) is Events.ClientLeftEvent:
            logging.debug(type(parsed_event))
        elif type(parsed_event) is Events.ClientMovedEvent:
            logging.debug(type(parsed_event))
        elif type(parsed_event) is Events.ClientMovedSelfEvent:
            logging.debug(type(parsed_event))
        elif type(parsed_event) is Events.ServerEditedEvent:
            logging.debug("Event of type " + str(type(parsed_event)))
            logging.debug(parsed_event.changed_properties)
        # Inform all observers
        self.inform_all(parsed_event)

    def get_obs_for_event(self, evt):
        obs = self.observers.get(type(evt), list())
        return obs

    def add_observer(self, obs, evt_type):
        obs_list = self.observers.get(evt_type, list())
        obs_list.append(obs)
        self.observers[evt_type] = obs_list

    def remove_observer(self, obs, evt_type):
        self.observers.get(evt_type, list()).remove(obs)

    def remove_observer_from_all(self, obs):
        for evt_type in self.observers.keys():
            self.remove_observer(obs, evt_type)

    def inform_all(self, evt):
        for o in self.get_obs_for_event(evt):
            try:
                threading.Thread(target=o(evt)).start()
            except Exception:
                EventHandler.logger.exception("Exception while informing " + str(o) + " of Event of type " +
                                              str(type(evt)) + "\nOriginal data:" + str(evt.data))
