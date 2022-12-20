# About

This plugin extends your bot with the feature to automatically move clients to an AFK channel, when they mark themself as "Away".


# Available Commands

The following table shows all available arguments for the command `!afkmover` of this plugin:

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
AfkMover: afk_mover.main
```

## Options

This plugin supports the following options:

| Option | Default | Description |
| ---: | :---: | :--- |
| `auto_start` | `True` | Either if the plugin should automatically start when the Bot starts and it's configured or not. |
| `enable_dry_run` | `False` | Set to `True`, if you want to test the plugin without executing the actual tasks. Instead it logs what it would have done. |
| `frequency` | `30.0` | The frequency in seconds how often (and fast) the plugin should react (e.g. somebody sets his own as "AFK", every 30 seconds the bot would notice this and do something). |
| `exclude_servergroups` | `None` | Provide a comma seperated list of servergroup names, which should never get moved by the bot. |
| `auto_move_back` | `True` | Either if clients, which are no longer AFK should be moved back to their original channel or not. |
| `resp_channel_settings` | `True` | Either if the channel settings like max. clients and password should be respected or not, even when the ServerQuery user could ignore them. |
| `fallback_channel` | `None` | Either to move a client, which could not be moved to the old channel due to an error (e.g. channel does not exist anymore or is full) to a different channel (provide the channel name pattern here) or leave him in the `channel` (set to `None`). |
| `channel` | `AFK` | The name of your AFK channel, where clients should be moved to while they are afk. |

If you need to change some of these default options, simply add them to your `config.ini` under the respective `ModuleName` section:

```
[afk_mover]
frequency: 10.0
exclude_servergroups: Server Admin,Bot
channel: Away
```

Please keep in mind, that you need to reload the plugin afterwards. Either by restarting the entire bot or by using a plugin command, if it has one.


# Required Permissions

This plugin requires the following permissions on your TeamSpeak server:

| Permission | Explanation |
| ---: | :--- |
| `b_virtualserver_client_list` | Allow the bot to get a list of all connected clients on your virtual server. |
| `i_channel_subscribe_power` | The bot must be able to subscribe channels, so that clients can be found in those channels. |
| `b_virtualserver_servergroup_list` | Allow the bot to get the list of available servergroups on your virtual server. |
| `b_virtualserver_channel_search` | Allow the bot to find a channel based on a name pattern. |
| `b_virtualserver_channel_list` | Allow the bot to list all channels. |
| `b_channel_info_view` | Allow the bot to view channel information. |
| `i_client_move_power` | Allow the bot to move clients. |
| `i_client_private_textmessage_power` | The bot will send in specific cases a private message to the client. If somebody wants to know the plugin version for example. |
