from ts3API.TS3Connection import TS3QueryException
from ts3API.utilities import TS3Exception

import Bot
import Moduleloader
from Moduleloader import *

__version__ = "0.5"
bot: Bot.Ts3Bot
logger = logging.getLogger("bot")

# defaults for configureable options
dry_run = False # log instead of performing actual actions

@Moduleloader.setup
def setup(ts3bot, enable_dry_run = dry_run):
    global bot, dry_run

    bot = ts3bot
    dry_run = enable_dry_run

    if dry_run:
        logger.info("Dry run is enabled - logging actions intead of actually performing them.")


@command('version', )
@group('Server Admin', 'Moderator')
def send_version(sender, _msg):
    """
    Sends a text message with the current version of this module to the `sender`.
    :param sender: Client id of sender that sent the command.
    """
    Bot.send_msg_to_client(bot.ts3conn, sender, f"The version of the `utils` plugin is `{__version__}`.")


@command('stop', )
@group('Server Admin')
def stop_bot(sender, _msg):
    """
    Stops the bot. An administrator needs to manually start it from the CLI again, if necessary.
    :param sender: Client id of sender that sent the command.
    """
    if dry_run:
        logger.info(f"Bot would have been stopped by clid={sender}, when dry-run would be disabled!")
        return

    Moduleloader.exit_all()
    bot.ts3conn.quit()
    logger.info(f"Bot has been stopped by clid={sender}!")


@command('restart', 'reload' )
@group('Server Admin', 'Moderator')
def restart_bot(sender, _msg):
    """
    Restarts the bot and thus reloads its configuration.
    :param sender: Client id of sender that sent the command.
    """
    if dry_run:
        logger.info(f"Bot would have been restarted by clid={sender}, when dry-run would be disabled!")
        return

    Moduleloader.exit_all()
    bot.ts3conn.quit()
    logger.info(f"Bot has been restarted by clid={sender}!")
    import main
    main.restart_program()


@command('help', 'commands', 'commandlist')
@group('Server Admin', 'Moderator')
def get_command_list(sender, _msg):
    """
    Sends a text message with the available bot commands to the `sender`.
    :param sender: Client id of sender that sent the command.
    """
    Bot.send_msg_to_client(bot.ts3conn, sender, "The following bot commands are available:")
    Bot.send_msg_to_client(bot.ts3conn, sender, str(list(bot.command_handler.handlers.keys())))


@command('multimove', 'mm')
@group('Server Admin', 'Moderator')
def multi_move(sender, msg):
    """
    Move multiple clients from one, multiple or all channels to a specific target channel at once.
    :param sender: Client id of sender that sent the command.
    :param msg: Sent command.
    """
    ts3conn = bot.ts3conn

    # evaluate and check command arguments
    source_channels = []
    target_channel = None

    try:
        command_args = msg.split('"')
        command_args = [cmd_arg for cmd_arg in command_args if cmd_arg.replace('"', '').replace("'", '').strip()]
        if len(command_args) != 3:
            raise ValueError

        _, source_channels, target_channel = command_args
    except ValueError:
        logger.error(f"Expected three values for this command, got instead: {msg}")

        try:
            Bot.send_msg_to_client(ts3conn, sender, "Your command was incorrect.")
            Bot.send_msg_to_client(ts3conn, sender, "Usage: !multimove 'all' 'targetChannelNamePattern'")
            Bot.send_msg_to_client(ts3conn, sender, "Usage: !multimove 'sourceChannelNamePattern' 'targetChannelNamePattern'")
            Bot.send_msg_to_client(ts3conn, sender, "Usage: !multimove 'sourceChannelNamePattern1;sourceChannelNamePattern2[;...]' 'targetChannelNamePattern'")
        except TS3QueryException:
            logger.exception(f"Failed to send the error message as textmessage to clid={sender}.")

        return

    # get source channel ID(s)
    source_channel_ids = []

    for source_channel_name_pattern in source_channels.split(';'):
        source_channel_name_pattern = source_channel_name_pattern.replace('"', '').replace("'", '').strip()

        logger.debug(f"Searching for a channel with the following name pattern: {str(source_channel_name_pattern)}")

        if source_channel_name_pattern == 'all':
            try:
                all_channels = ts3conn.channellist()
            except TS3Exception:
                logger.exception(f"Error getting `all` channels.")

                try:
                    Bot.send_msg_to_client(ts3conn, sender, f"Could not get all channels.")
                except TS3QueryException:
                    logger.error(f"Failed to send the info message as textmessage to clid={sender}.")

            for channel in all_channels:
                source_channel_ids.append(int(channel.get("cid", '-1')))
        else:
            try:
                matching_source_channels = ts3conn.channelfind(source_channel_name_pattern)
                for matching_source_channel in matching_source_channels:
                    source_channel_ids.append(int(matching_source_channel.get("cid", "-1")))
            except TS3Exception:
                logger.exception(f"Error getting `{source_channel_name_pattern}` channel.")

                try:
                    Bot.send_msg_to_client(ts3conn, sender, f"Could not find any channel with the name `{source_channel_name_pattern}`.")
                except TS3QueryException:
                    logger.error(f"Failed to send the info message as textmessage to clid={sender}.")

    if len(source_channel_ids) == 0:
        logger.error(f"Could not find any source channel for the given channel name pattern(s): {str(source_channels)}")

        try:
            Bot.send_msg_to_client(ts3conn, sender, f"Could not find any source channel for the given channel name pattern(s): {str(source_channels)}")
            Bot.send_msg_to_client(ts3conn, sender, "Please ensure, that the channel name pattern(s) are correct.")
        except TS3QueryException:
            logger.error(f"Failed to send the info message as textmessage to clid={sender}.")

        return

    logger.debug(f"Source channel IDs: {str(source_channel_ids)}.")

    # get target channel ID
    target_channel_id = None

    try:
        target_channel_id = int(ts3conn.channelfind(target_channel)[0].get("cid", '-1'))
    except TS3Exception:
        logger.exception(f"Error getting `{target_channel}` channel.")

        try:
            Bot.send_msg_to_client(ts3conn, sender, f"Could not find any channel with the name `{target_channel}`.")
        except TS3QueryException:
            logger.error(f"Failed to send the info message as textmessage to clid={sender}.")

    if target_channel_id is None or not isinstance(target_channel_id, int):
        logger.error(f"Could not find any target channel for the given channel name pattern: {str(target_channel)}")

        try:
            Bot.send_msg_to_client(ts3conn, sender, f"Could not find any target channel for the given channel name pattern: {str(target_channel)}")
            Bot.send_msg_to_client(ts3conn, sender, "Please ensure, that the channel name pattern is correct and matches only a single channel.")
        except TS3QueryException:
            logger.error(f"Failed to send the info message as textmessage to clid={sender}.")

        return

    if isinstance(target_channel_id, list):
        logger.error(f"Found multiple target channels for the given channel name pattern, but only one is supported: {str(target_channel)}")

        try:
            Bot.send_msg_to_client(ts3conn, sender, f"Found multiple target channels for the given channel name pattern, but only one is supported: {str(target_channel)}")
            Bot.send_msg_to_client(ts3conn, sender, "Please ensure, that the channel name pattern is correct and matches only a single channel.")
        except TS3QueryException:
            logger.error(f"Failed to send the info message as textmessage to clid={sender}.")

        return

    logger.debug(f"Target channel ID: {int(target_channel_id)}.")

    # get all current connected clients
    all_clients = None

    try:
        all_clients = ts3conn.clientlist()
    except TS3QueryException:
        logger.error(f"Failed to send the info message as textmessage to clid={sender}.")

    if all_clients is None or len(all_clients) == 0:
        logger.error("Could not find any client on the TeamSpeak server.")

        try:
            Bot.send_msg_to_client(ts3conn, sender, "Could not find any client on the TeamSpeak server.")
        except TS3QueryException:
            logger.error(f"Failed to send the info message as textmessage to clid={sender}.")

        return

    logger.info(f"Found {len(all_clients)} currently connected clients.")

    # filter client list to get only clients, which should be moved
    filtered_clients = []

    for client in all_clients:
        if int(client.get('client_type')) == 1:
            logger.debug(f"Ignoring ServerQuery client: {client}")
            continue

        if int(client.get('cid')) not in source_channel_ids:
            logger.debug(f"Ignoring client as not member of any source channel: {client}")
            continue

        logger.debug(f"Client is member of a source channel. Adding to the move list: {client}")
        filtered_clients.append(client)

    if len(filtered_clients) == 0:
        logger.error("Could not find any client in the source channel(s).")

        try:
            Bot.send_msg_to_client(ts3conn, sender, "Could not find any client in the source channel(s).")
            Bot.send_msg_to_client(ts3conn, sender, "Please ensure, that you have provided the correct channel name pattern(s).")
        except TS3QueryException:
            logger.error(f"Failed to send the info message as textmessage to clid={sender}.")

        return

    logger.info(f"Found {len(filtered_clients)} clients in all respective source channels.")
    logger.debug(f"Client list to move: {str(filtered_clients)}.")

    # move all clients to the target channel
    for client in filtered_clients:
        try:
            if dry_run:
                logger.info(f"Would have moved the following client to the channel ID {int(target_channel_id)}, if the dry-run would be disabled: {str(client)}")
            else:
                ts3conn.clientmove(int(target_channel_id), int(client.get("clid", '-1')))
        except TS3QueryException as e:
            # Error: already member of channel
            if int(e.id) == 770:
                return

            Bot.send_msg_to_client(ts3conn, sender, f"Failed to move the client `{client.get('client_nickname')}`: id={str(e.id)} error_message={str(e.message)}")
