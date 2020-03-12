#!/usr/bin/env python3
import Bot
import sys
import logging
import threading
import os
from ts3.utilities import TS3ConnectionClosedException

logger = None
bot = None


def exception_handler(exctype, value, tb):
    """
    Exception handler to prevent any exceptions from printing to stdout. Logs all exceptions to the logger.
    :param exctype: Exception type
    :param value: Exception value
    :param tb: Exception traceback
    :return:
    """
    logger.error("Uncaught exception.", exc_info=(exctype, value, tb))


def restart_program():
    """
    Restarts the current program.
    Note: this function does not return. Any cleanup action (like
    saving data) must be done before calling this function.
    """
    python = sys.executable
    os.execl(python, python, * sys.argv)


def main():
    """
    Start the bot, set up logger and set exception hook.
    :return:
    """
    run_old = threading.Thread.run

    def run(*args, **kwargs):
        try:
            run_old(*args, **kwargs)
        except (KeyboardInterrupt, SystemExit, TS3ConnectionClosedException):
            # This is a very ungraceful exit!
            os._exit(-1)
            raise
        except:
            sys.excepthook(*sys.exc_info())
    threading.Thread.run = run
    global bot, logger
    logger = logging.getLogger("bot")
    if not logger.hasHandlers():
        logger.propagate = 0
        logger.setLevel(logging.INFO)
        file_handler = logging.FileHandler("bot.log", mode='a+')
        formatter = logging.Formatter("%(asctime)s: %(levelname)s: %(message)s")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.info('Started')
    sys.excepthook = exception_handler
    config = Bot.Ts3Bot.parse_config(logger)
    bot = Bot.Ts3Bot.bot_from_config(config)

if __name__ == "__main__":
    main()
