"""EventHandler for the Teamspeak3 Bot."""
import logging
import threading

import ts3API.Events as Events


class EventHandler(object):
    """
    EventHandler class responsible for delegating events to registered listeners.
    """
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

    def on_event(self, _sender, **kw):
        """
        Called upon a new event. Logs the event and informs all listeners.
        """
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
        elif isinstance(parsed_event, Events.ClientLeftEvent):
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
        """
        Get all observers for an event.
        :param evt: Event to get observers for.
        :return: List of observers.
        :rtype: list[function]
        """
        obs = set()
        for t in type(evt).mro():
            obs.update(self.observers.get(t, set()))
        return obs

    def add_observer(self, obs, evt_type):
        """
        Add an observer for an event type.
        :param obs: Function to call upon a new event of type evt_type.
        :param evt_type: Event type to observe.
        :type evt_type: TS3Event
        """
        obs_set = self.observers.get(evt_type, set())
        obs_set.add(obs)
        self.observers[evt_type] = obs_set

    def remove_observer(self, obs, evt_type):
        """
        Remove an observer for an event type.
        :param obs: Observer to remove.
        :param evt_type: Event type to remove the observer from.
        """
        self.observers.get(evt_type, set()).discard(obs)

    def remove_observer_from_all(self, obs):
        """
        Removes an observer from all event_types.
        :param obs: Observer to remove.
        """
        for evt_type in self.observers.keys():
            self.remove_observer(obs, evt_type)

    # We really want to catch all exception here, to prevent one observer from crashing the bot
    # noinspection PyBroadException
    def inform_all(self, evt):
        """
        Inform all observers registered to the event type of an event.
        :param evt: Event to inform observers of.
        """
        for o in self.get_obs_for_event(evt):
            try:
                threading.Thread(target=o(evt)).start()
            except BaseException:
                EventHandler.logger.exception("Exception while informing %s of Event of type "
                                              "%s\nOriginal data: %s", str(o), str(type(evt)),
                                              str(evt.data))
