from ts3API.TS3Connection import TS3QueryException
import ts3API.Events as Events

import Bot
import Moduleloader
from Moduleloader import *

bot: None
# Server groups who should not receiver quotes upon joining the server
dont_send = []

channel_config = {}
channels_configured = []



@Moduleloader.setup
def setup_communityservice(ts3bot):
    """
    Setup the quoter. Define groups not to send quotes to.
    :return:
    """  
    global bot
    bot = ts3bot
    ts3conn = bot.ts3conn

    global channel_config
    global channels_configured
    channel_config = {int(k):v for k,v in config["channel_config"].items()}
    channels_configured = list(channel_config.keys())
    name = config["name"]

@Moduleloader.channel_event(Events.ClientMovedSelfEvent, 0)
def on_channel_join_event(evt):
    """
    Create a temporary channel 
    """

    if evt.target_channel_id in channels_configured:
        # Gather all information first:
        curr_ch_cfg = channel_config[evt.target_channel_id]
        channel_name = curr_ch_cfg["cname"].format(curr_ch_cfg["currnum"])
        channel_topic = curr_ch_cfg["ctopic"]
        channel_maxc = curr_ch_cfg["cuser"]
        curr_ch_cfg["currnum"] += 1

        # Create Channel, move user to it, leave and join homechannel
        createAsSub = True
        if "createassub" in curr_ch_cfg:
            createAsSub = curr_ch_cfg["createassub"]
                
        if createAsSub == True:
            response = _get_channel_info(evt.target_channel_id)            
            cpid = evt.target_channel_id
            response = _channel_create(["channel_name=" + channel_name,"channel_topic=" + channel_topic, "channel_maxclients=" + str(channel_maxc)])
            cid = response["cid"]
            response = _channel_move(["cid=" + cid, "cpid=" + str(cpid)])

        else:
            response = _get_channel_info(evt.target_channel_id)
            cpid = response["pid"]    
            response = _channel_create(["channel_name=" + channel_name,"channel_topic=" + channel_topic, "channel_maxclients=" + str(channel_maxc) ])
            cid = response["cid"]
            response = _channel_move(["cid=" + cid, "cpid=" + str(cpid), "order=" + str(evt.target_channel_id)])
        bot.ts3conn.clientmove(int(cid), evt.client_id)
        _bot_go_home()

def on_channel_message_event(_sender, **kw):
    pass

def _bot_go_home():
    """
    Just go to your homechannel boi.
    """
    bot.ts3conn.clientmove(1045, int(bot.ts3conn.whoami()["client_id"])) #bot.default_channel

def _channel_create(param):
    """
    Create a new channel.
    :param param: parameter used by channel_create qry
    :return: Response from query decoded to dict
    """
    return bot.ts3conn._parse_resp_to_dict(
        bot.ts3conn._send("channelcreate", param))

def _channel_move(param):
    """
    Move a new channel.
    :param param: parameter used by channel_move qry
    :return: Response from query decoded to dict
    """
    return bot.ts3conn._parse_resp_to_dict(
        bot.ts3conn._send("channelmove", param))

def _get_channel_info(cid):
    """
    Get channel info
    :param cid: Channel ID
    :return: Response from query decoded to dict
    """
    return bot.ts3conn._parse_resp_to_dict(
        bot.ts3conn._send("channelinfo", ["cid=" + str(cid)]))
    
