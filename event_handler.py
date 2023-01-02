# standard imports
import logging
import threading

# third-party imports
from ts3API.Events import (
    TextMessageEvent,
    ChannelEditedEvent,
    ChannelDescriptionEditedEvent,
    ClientEnteredEvent,
    ClientLeftEvent,
    ClientMovedEvent,
    ClientMovedSelfEvent,
    ServerEditedEvent,
)


class EventHandler:
    """
    EventHandler class responsible for delegating events to registered listeners.
    """

    # configure logger
    class_name = __qualname__
    logger = logging.getLogger(class_name)
    logger.propagate = 0
    logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler(f"logs/{class_name.lower()}.log", mode="a+")
    formatter = logging.Formatter("%(asctime)s: %(levelname)s: %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.info("Configured %s logger", str(class_name))
    logger.propagate = 0

    def __init__(self, ts3conn, command_handler):
        self.ts3conn = ts3conn
        self.command_handler = command_handler
        self.observers = {}
        self.add_observer(self.command_handler.inform, TextMessageEvent)

    def on_event(self, _sender, **kw):
        """
        Called upon a new event. Logs the event and informs all listeners.
        """
        # parsed_event = Events.EventParser.parse_event(event=event)
        parsed_event = kw["event"]
        if isinstance(parsed_event, TextMessageEvent):
            logging.debug(type(parsed_event))
        elif isinstance(parsed_event, ChannelEditedEvent):
            logging.debug(type(parsed_event))
        elif isinstance(parsed_event, ChannelDescriptionEditedEvent):
            logging.debug(type(parsed_event))
        elif isinstance(parsed_event, ClientEnteredEvent):
            logging.debug(type(parsed_event))
        elif isinstance(parsed_event, ClientLeftEvent):
            logging.debug(type(parsed_event))
        elif isinstance(parsed_event, ClientMovedEvent):
            logging.debug(type(parsed_event))
        elif isinstance(parsed_event, ClientMovedSelfEvent):
            logging.debug(type(parsed_event))
        elif isinstance(parsed_event, ServerEditedEvent):
            logging.debug("Event of type %s", str(type(parsed_event)))
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
        for evt_type in self.observers:
            self.remove_observer(obs, evt_type)

    # We really want to catch all exception here, to prevent one observer from crashing the bot
    # noinspection PyBroadException
    def inform_all(self, evt):
        """
        Inform all observers registered to the event type of an event.
        :param evt: Event to inform observers of.
        """
        for observer in self.get_obs_for_event(evt):
            try:
                threading.Thread(target=observer(evt)).start()
            except BaseException:
                EventHandler.logger.exception(
                    "Exception while informing %s of Event of type "
                    "%s\nOriginal data: %s",
                    str(observer),
                    str(type(evt)),
                    str(evt.data),
                )
