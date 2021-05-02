from ts3API.TS3Connection import TS3QueryException
import ts3API.Events as Events

import Bot
import Moduleloader
from Moduleloader import *

from modules.ufrasettings import *

bot: None
# Server groups who should not receiver quotes upon joining the server
dont_send = []


channel_config = {
                    1047:{
                        "cname":"Zug Channel {0}",                        
                        "currnum": 0,
                        "ctopic": "Temporary channel for playing in platoon",
                        "cuser": 5
                        },
                    1178:{
                        "cname":"Stream Channel {0}",                        
                        "currnum": 0,
                        "ctopic": "Temporary channel for playing in platoon",
                        "cuser": 5
                        },
                }

@Moduleloader.setup
def setup_communityservice(ts3bot):
    """
    Setup the quoter. Define groups not to send quotes to.
    :return:
    """  
    #global bot, dont_send
    groups = [group_henker, group_officier]

    global bot
    bot = ts3bot
    ts3conn = bot.ts3conn

@Moduleloader.channel_event(Events.ClientMovedSelfEvent, 1047, 1045,)
def on_channel_join_event(evt):
    """
    Create a temporary channel 
    """

    # Gather all information first:
    curr_ch_cfg = channel_config[evt.target_channel_id]
    channel_name = curr_ch_cfg["cname"].format(curr_ch_cfg["currnum"])
    channel_topic = curr_ch_cfg["ctopic"]
    channel_maxc = curr_ch_cfg["cuser"]
    curr_ch_cfg["currnum"] += 1

    # Create Channel, move user to it, leave and join homechannel
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
    
