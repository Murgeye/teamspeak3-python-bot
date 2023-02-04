# standard imports
import logging
import threading
from threading import Thread
from typing import Union

# third-party imports
from ts3API.utilities import TS3Exception
import openai

# local imports
from module_loader import setup_plugin, exit_plugin, command, group
import teamspeak_bot

PLUGIN_VERSION = 0.1
PLUGIN_COMMAND_NAME = "chatgpt"
PLUGIN_INFO: Union[None, "ChatGPT"] = None
PLUGIN_STOPPER = threading.Event()
BOT: teamspeak_bot.Ts3Bot

# defaults for configureable options
AUTO_START = True
DRY_RUN = False  # log instead of performing actual actions
OPENAI_API_KEY = None  # The OpenAI API key


class ChatGPT(Thread):
    """
    ChatGPT class. Awaits a text message from a client and responds accordingly.
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

    def __init__(self, stop_event, ts3conn):
        """
        Create a new ChatGPT object.
        :param stop_event: Event to signalize the ChatGPT to stop.
        :type stop_event: threading.Event
        :param ts3conn: Connection to use
        :type: TS3Connection
        """
        Thread.__init__(self)
        self.stopped = stop_event
        self.ts3conn = ts3conn

        self.openai_api_key = OPENAI_API_KEY


@command(f"{PLUGIN_COMMAND_NAME} ask")
@group(".*")
def ask_chatgpt(sender=None, msg=None):
    """
    Sends text to ChatGPT, awaits its response and sends it as textmessage to the `sender`.
    """
    chatgpt_prompt = msg.replace(f"!{PLUGIN_COMMAND_NAME} ask", "").strip()

    if len(chatgpt_prompt) == 0:
        try:
            teamspeak_bot.send_msg_to_client(
                BOT.ts3conn,
                sender,
                "You need to provide some text to ChatGPT, so that it can react to it.",
            )
        except TS3Exception:
            ChatGPT.logger.exception(
                "Error while sending the info that text for ChatGPT is missing as a message to the client!"
            )
        return

    try:
        teamspeak_bot.send_msg_to_client(
            BOT.ts3conn,
            sender,
            "I'm on it. Give me a few seconds...",
        )
    except TS3Exception:
        ChatGPT.logger.exception(
            "Error while sending the plugin version as a message to the client!"
        )

    openai.api_key = str(PLUGIN_INFO.openai_api_key)
    model_engine = "text-davinci-003"

    try:
        completion = openai.Completion.create(
            engine=model_engine,
            prompt=chatgpt_prompt,
            max_tokens=1024,
            n=1,
            stop=None,
            temperature=0.5,
        )
    except openai.error.AuthenticationError as auth_error:
        ChatGPT.logger.error("Authentication failed: %s", str(auth_error))

        try:
            teamspeak_bot.send_msg_to_client(
                BOT.ts3conn,
                sender,
                "The authentication to the ChatGPT server failed. Please inform your administrator to check this issue.",
            )
        except TS3Exception:
            ChatGPT.logger.exception(
                "Error: Could not inform the client, that the ChatGPT authentication failed."
            )

        return

    try:
        chatgpt_response = completion.choices[0].text.strip("\n")
    except IndexError:
        ChatGPT.logger.error("ChatGPT did not return any choices: %s", str(completion))

        try:
            teamspeak_bot.send_msg_to_client(
                BOT.ts3conn,
                sender,
                "ChatGPT did not return any response. Please try again. Maybe with a different wording.",
            )
        except TS3Exception:
            ChatGPT.logger.exception(
                "Error: Could not inform the client, that ChatGPT did not return any response."
            )

        return

    max_textmessage_length = 1023
    chatgpt_response_splitted = [
        chatgpt_response[i : i + max_textmessage_length]
        for i in range(0, len(chatgpt_response), max_textmessage_length)
    ]

    for response in chatgpt_response_splitted:
        try:
            teamspeak_bot.send_msg_to_client(
                BOT.ts3conn,
                sender,
                str(response),
            )
        except TS3Exception:
            ChatGPT.logger.exception(
                "Error: Failed to send the ChatGPT response to the client!"
            )


@command(f"{PLUGIN_COMMAND_NAME} version")
def send_version(sender=None, _msg=None):
    """
    Sends the plugin version as textmessage to the `sender`.
    """
    try:
        teamspeak_bot.send_msg_to_client(
            BOT.ts3conn,
            sender,
            f"This plugin is installed in the version `{str(PLUGIN_VERSION)}`.",
        )
    except TS3Exception:
        ChatGPT.logger.exception(
            "Error while sending the plugin version as a message to the client!"
        )


@command(f"{PLUGIN_COMMAND_NAME} start")
def start_plugin(_sender=None, _msg=None):
    """
    Start the ChatGPT by clearing the PLUGIN_STOPPER signal and starting the plugin.
    """
    global PLUGIN_INFO
    if PLUGIN_INFO is None:
        if DRY_RUN:
            ChatGPT.logger.info(
                "Dry run is enabled - logging actions intead of actually performing them."
            )

        PLUGIN_INFO = ChatGPT(PLUGIN_STOPPER, BOT.ts3conn)
        PLUGIN_STOPPER.clear()
        PLUGIN_INFO.start()


@command(f"{PLUGIN_COMMAND_NAME} stop")
def stop_plugin(_sender=None, _msg=None):
    """
    Stop the ChatGPT by setting the PLUGIN_STOPPER signal and undefining the plugin.
    """
    global PLUGIN_INFO
    PLUGIN_STOPPER.set()
    PLUGIN_INFO = None


@command(f"{PLUGIN_COMMAND_NAME} restart")
def restart_plugin(_sender=None, _msg=None):
    """
    Restarts the plugin by executing the respective functions.
    """
    stop_plugin()
    start_plugin()


@setup_plugin
def setup(
    ts3bot,
    auto_start=AUTO_START,
    enable_dry_run=DRY_RUN,
    openai_api_key=OPENAI_API_KEY,
):
    """
    Sets up this plugin.
    """
    global BOT, AUTO_START, DRY_RUN, OPENAI_API_KEY

    BOT = ts3bot
    AUTO_START = auto_start
    DRY_RUN = enable_dry_run
    OPENAI_API_KEY = openai_api_key

    if AUTO_START:
        start_plugin()


@exit_plugin
def exit_module():
    """
    Exits this plugin gracefully.
    """
    global PLUGIN_INFO

    if PLUGIN_INFO is not None:
        PLUGIN_STOPPER.set()
        PLUGIN_INFO.join()
        PLUGIN_INFO = None
