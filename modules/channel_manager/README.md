# About

This plugin extends your bot with the feature to automatically create new channels, when necessary.

Define for example a group of "Talk" channels. Tell the bot how many of these channels you always want to have, even
when nobody is in it. If all of these channels have at least one client in it, the bot will automatically create an
additional channel as long as clients are filling all of those "Talk" channels. If a channel is empty again, the bot
will automatically it, until you only have your defined minium amount of channels and/or at least one empty channel.


# Available Commands

The following table shows all available arguments for the command `!channelmanager` of this plugin:

| Argument | Description |
| ---: | :--- |
| `version` | Sends a text message with the version of this plugin. |
| `start` | Start this plugin |
| `stop` | Stop this plugin |
| `restart` | Restarts this plugin |


# Configuration

Enable this plugin by adding the following line under the `Plugins` section to your `config.ini`:

```
[Plugins]
ChannelManager: channel_manager.main
```

## Options

This plugin supports the following general options:

| Option | Default | Description |
| ---: | :---: | :--- |
| `auto_start` | `True` | Either if the plugin should automatically start when the Bot starts and it's configured or not. |
| `enable_dry_run` | `False` | Set to `True`, if you want to test the plugin without executing the actual tasks. Instead it logs what it would have done. |

This plugin supports the following channel options:

> **_NOTE:_** `<alias>` can be anything - it's only used to differentiate between multiple channel configurations. Supported characters for the `alias`: `a-z`, `A-Z`, `0-9_`

| Option | Default | Description |
| ---: | :---: | :--- |
| `<alias>.parent_channel_name` | `None` | Set a unique channel name pattern under which those channels should be created. |
| `<alias>.name_prefix` | `None` | Sets the prefix of the channel name. Example: `Talk` will become `Talk 1`, `Talk 2`, etc.. |
| `<alias>.minimum` | `1` | Defines how many of this channel you always want to have, even when no client is in it. Must be `1` or greater. |
| `<alias>.<channel_property>` | `None` | Optionally set any officially available channel property like `channel_description` or `channel_maxclients`. |
| `<alias>.<channel_permission_name>` | `None` | Optionally set any officially available channel permission name like `i_channel_needed_join_power` or `i_ft_needed_file_browse_power`. |

If you need to change some of these default options, simply add them to your `config.ini` under the respective `ModuleName` section:

```
[channel_manager]
talk.parent_channel_name: Talk Area
talk.name_prefix: Just Talking

bf2042_squad.parent_channel_name: cspacer15
bf2042_squad.name_prefix: Battlefield 2042 Squad
bf2042_squad.channel_description: Let's play BF2042!
bf2042_squad.channel_maxclients: 4
bf2042_squad.i_icon_id: 1568885232
bf2042_squad.i_ft_needed_file_browse_power: 75

pubg_duo.parent_channel_name: PUBG
pubg_duo.name_prefix: Duo
pubg_duo.channel_maxclients: 2
pubg_duo.i_icon_id: 2916663205

pubg_squad.parent_channel_name: PUBG
pubg_squad.name_prefix: Squad
pubg_squad.channel_maxclients: 4
pubg_squad.i_icon_id: 2916663205
```

Please keep in mind, that you need to reload the plugin afterwards. Either by restarting the entire bot or by using a plugin command, if it has one.


# Required Permissions

This plugin requires the following permissions on your TeamSpeak server:

| Permission | Explanation |
| ---: | :--- |
| `b_virtualserver_notify_register` | Allow the bot to register for specific events. |
| `b_virtualserver_channel_list` | Allow the bot to list all channels. |
| `b_virtualserver_client_list` | Allow the bot to get a list of all connected clients on your virtual server. |
| `i_channel_subscribe_power` | The bot must be able to subscribe channels, so that clients can be found in those channels. |
| `b_virtualserver_channel_search` | Allow the bot to find a channel based on a name pattern. |
| `b_channel_create_child` | Allow the bot to create a semi-permanent channel with the specified channel properties. |
| `b_channel_create_semi_permanent` | Allow the bot to create a semi-permanent channel with the specified channel properties. |
| `b_channel_create_with_topic` | Allow the bot to create a semi-permanent channel with the specified channel properties. |
| `b_channel_create_with_description` | Allow the bot to create a semi-permanent channel with the specified channel properties. |
| `b_channel_create_with_password` | Allow the bot to create a semi-permanent channel with the specified channel properties. |
| `b_channel_create_with_banner` | Allow the bot to create a semi-permanent channel with the specified channel properties. |
| `i_channel_create_modify_with_codec_maxquality` | Allow the bot to create a semi-permanent channel with the specified channel properties. |
| `i_channel_create_modify_with_codec_latency_factor_min` | Allow the bot to create a semi-permanent channel with the specified channel properties. |
| `b_channel_create_with_maxclients` | Allow the bot to create a semi-permanent channel with the specified channel properties. |
| `b_channel_create_with_maxfamilyclients` | Allow the bot to create a semi-permanent channel with the specified channel properties. |
| `b_channel_create_with_sortorder` | Allow the bot to create a semi-permanent channel with the specified channel properties. |
| `b_channel_create_with_default` | Allow the bot to create a semi-permanent channel with the specified channel properties. |
| `b_channel_create_with_needed_talk_power` | Allow the bot to create a semi-permanent channel with the specified channel properties. |
| `b_channel_delete_semi_permanent` | Allow the bot to delete the semi-permanent channels, created by this plugin. |
| `i_client_private_textmessage_power` | The bot will send in specific cases a private message to the client. If somebody wants to know the plugin version for example. |
