# About

This plugin extends your bot with the feature to automatically open and close a supporter channel, when one or more clients of specific servergroups are online or offline.

It will rename the channel and suffix it with `[OPEN]` or `[CLOSED]` depending on the status and additional, it will also set the channel property `channel_maxclients` to either `-1` (unlimited) or `0` (nobody).


# Available Commands

The following table shows all available arguments for the command `!switchsupporterchannelstatus` of this plugin:

| Argument | Description |
| ---:   | :--- |
| `version` | Sends a text message with the version of this plugin. |
| `start` | Start this plugin |
| `stop` | Stop this plugin |
| `restart` | Restarts this plugin |


# Configuration

Enable this plugin by adding the following line under the `Plugins` section to your `config.ini`:

```
[Plugins]
SwitchSupporterChannelStatus: switch_supporter_channel_status.main
```


## Options

This plugin supports the following options:

| Option | Default | Description |
| ---: | :---: | :--- |
| `auto_start` | `True` | Either if the plugin should automatically start when the Bot starts and it's configured or not. |
| `enable_dry_run` | `False` | Set to `True`, if you want to test the plugin without executing the actual tasks. Instead it logs what it would have done. |
| `supporter_channel_name` | `Support Lobby` | The name of the supporter channel, which should be opened or closed. |
| `servergroups_to_check` | `N/A` | Define a comma seperated list of servergroup name patterns, which should be checked for online clients. |
| `minimum_online_clients` | `1` | Define the minimum amount of online clients from the above servergroups to open the support channel. |
| `afk_channel_name` | `N/A` | Define the name of your AFK channel to exclude supporter clients, which are away. |

If you need to change some of these default options, simply add them to your `config.ini` under the respective `ModuleName` section:

```
[switch_supporter_channel_status]
supporter_channel_name: Support
servergroups_to_check: Moderator,Supporter
minimum_online_clients: 3
afk_channel_name: Away
```

Please keep in mind, that you need to reload the plugin afterwards. Either by restarting the entire bot or by using a plugin command, if it has one.


# Required Permissions

This plugin requires the following permissions on your TeamSpeak server:

| Permission | Explanation |
| ---: | :--- |
| `b_virtualserver_notify_register` | Allow the bot to register for specific events. |
| `b_virtualserver_channel_search` | Allow the bot to find a channel based on a name pattern. |
| `b_virtualserver_servergroup_list` | Allow the bot to get the list of available servergroups on your virtual server. |
| `b_virtualserver_servergroup_client_list` | Allow the bot to get the member list of a specific servergroup. |
| `b_virtualserver_client_list` | Allow the bot to get a list of all connected clients on your virtual server. |
| `i_channel_subscribe_power` | The bot must be able to subscribe channels, so that clients can be found in those channels. |
| `b_channel_info_view` | Allow the bot to view channel information. |
| `i_channel_modify_power` | Allow the bot to modify your supporter channel. |
| `b_channel_modify_name` | Allow the bot to edit the name of your supporter channel. |
| `b_channel_modify_maxclients` | Allow the bot to edit the maxclients of your supporter channel. |
| `i_client_private_textmessage_power` | The bot will send in specific cases a private message to the client. If somebody wants to know the plugin version for example. |
