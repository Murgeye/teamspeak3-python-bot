#!/usr/bin/env python3
import Bot
from importlib import reload
import sys
import logging
import threading
import traceback
import os

logger = None
bot = None


def exception_handler(exctype, value, tb):
    logger.exception("Uncaught exception:" + str(exctype))
    logger.error(str(value))
    logger.error(traceback.format_exc())


def reload_bot(botarg):
    global bot
    botarg.close()
    reload(Bot)
    bot = Bot.Ts3Bot()


def restart_program():
    """
    Restarts the current program.
    Note: this function does not return. Any cleanup action (like
    saving data) must be done before calling this function.
    """
    python = sys.executable
    #print(python, sys.argv)
    os.execl(python, python, * sys.argv)


def main():
    run_old = threading.Thread.run

    def run(*args, **kwargs):
        try:
            run_old(*args, **kwargs)
        except (KeyboardInterrupt, SystemExit):
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
    bot = Bot.Ts3Bot()

if __name__ == "__main__":
    main()
