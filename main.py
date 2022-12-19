#!/usr/bin/env python3

# standard imports
import logging
import os
import sys
import threading

# third-party imports
from ts3API.utilities import TS3ConnectionClosedException

# local imports
import teamspeak_bot

LOGGER = None
BOT = None


def exception_handler(exctype, value, exception_tb):
    """
    Exception handler to prevent any exceptions from printing to stdout. Logs all exceptions to the LOGGER.
    :param exctype: Exception type
    :param value: Exception value
    :param exception_tb: Exception traceback
    :return:
    """
    LOGGER.error("Uncaught exception.", exc_info=(exctype, value, exception_tb))


def restart_program():
    """
    Restarts the current program.
    Note: this function does not return. Any cleanup action (like
    saving data) must be done before calling this function.
    """
    python = sys.executable
    os.execl(python, python, *sys.argv)


def main():
    """
    Start the BOT, set up LOGGER and set exception hook.
    :return:
    """
    run_old = threading.Thread.run

    def run(*args, **kwargs):
        try:
            run_old(*args, **kwargs)
        except (KeyboardInterrupt, SystemExit, TS3ConnectionClosedException):
            raise
        except:
            sys.excepthook(*sys.exc_info())

    threading.Thread.run = run

    try:
        os.makedirs(os.path.realpath("logs"))
    except FileExistsError:
        pass

    global BOT, LOGGER
    LOGGER = logging.getLogger("BOT")

    if not LOGGER.hasHandlers():
        class_name = "Bot"
        LOGGER = logging.getLogger(class_name)
        LOGGER.propagate = 0
        LOGGER.setLevel(logging.INFO)
        file_handler = logging.FileHandler(f"logs/{class_name.lower()}.log", mode="a+")
        formatter = logging.Formatter("%(asctime)s: %(levelname)s: %(message)s")
        file_handler.setFormatter(formatter)
        LOGGER.addHandler(file_handler)
        LOGGER.info("Configured %s logger", str(class_name))
        LOGGER.propagate = 0

    sys.excepthook = exception_handler
    config = teamspeak_bot.Ts3Bot.parse_config(LOGGER)
    BOT = teamspeak_bot.Ts3Bot.bot_from_config(config)


if __name__ == "__main__":
    main()
