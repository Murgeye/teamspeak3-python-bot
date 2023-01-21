# About

This plugin extends your bot with the feature to automatically poke clients, when a client joins a specific channel.

Let for example your support team know, that somebody joined the support channel and also inform the client, that your
support team has been informed about it.


# Available Commands

The following table shows all available arguments for the command `!pokeclientonchanneljoin` of this plugin:

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
PokeClientOnChannelJoin: poke_client_on_channel_join.main
```

## Options

This plugin supports the following general options:

| Option | Default | Description |
| ---: | :---: | :--- |
| `auto_start` | `True` | Either if the plugin should automatically start when the Bot starts and it's configured or not. |
| `enable_dry_run` | `False` | Set to `True`, if you want to test the plugin without executing the actual tasks. Instead it logs what it would have done. |

This plugin supports the following options per channel:

> **_NOTE:_** `<alias>` can be anything - it's only used to differentiate between multiple channel configurations. Supported characters for the `alias`: `a-z`, `A-Z`, `0-9`, `_`

| Option | Default | Description |
| ---: | :---: | :--- |
| `<alias>.channel_name` | `None` | The name of the channel, which clients need to join to poke other clients. |
| `<alias>.team_servergroups` | `None` | Optionally define a comma seperated list of servergroup name patterns, which should get poked. This requires `team_poke_message` to be defined. |
| `<alias>.team_poke_message` | `None` | Optionally define the poke message, which will be sent to all members of the `team_servergroups`. Supported variables: `%u` (the clients nickname, which receives the poke message), `%c` (the clients nickname, which joined the channel) (Max. poke message length is 100 characters.) |
| `<alias>.user_poke_message` | `None` | Optionally define the poke message, which will be sent to the client, which joined the channel. Supported variables: `%u` (the clients nickname, which receives the poke message) (Max. poke message length is 100 characters.) |

If you need to change some of these default options, simply add them to your `config.ini` under the respective `ModuleName` section:

```
[poke_client_on_channel_join]
enable_dry_run: True

support.channel_name: Support Lobby
support.team_servergroups: Supporter,Moderator
support.team_poke_message: Hello %u! %c needs support.
support.user_poke_message: Hello %u! The support team is informed.

other_channel.channel_name: Some Channel Name
other_channel.team_servergroups: Moderator
other_channel.team_poke_message: Hello! Someone joined the channel.

create_own_channel.channel_name: Create your own channel
create_own_channel.user_poke_message: Hello %u! Edit your channel to your needs.
```

Please keep in mind, that you need to reload the plugin afterwards. Either by restarting the entire bot or by using a plugin command, if it has one.


# Required Permissions

This plugin requires the following permissions on your TeamSpeak server:

| Permission | Explanation |
| ---: | :--- |
| `b_virtualserver_notify_register` | Allow the bot to register for specific events. |
| `b_virtualserver_channel_search` | Allow the bot to search for a channel based on a name pattern. |
| `b_virtualserver_servergroup_list` | Allow the bot list all servergroups to be able to exclude clients. |
| `b_virtualserver_servergroup_client_list` | Allow the bot to get a list of clients of your servergroups. |
| `i_client_poke_power` | Allow the bot to poke the newbie and respective team members. |
| `b_virtualserver_client_list` | Allow the bot to get a list of all connected clients on your virtual server. |
| `i_channel_subscribe_power` | The bot must be able to subscribe channels, so that clients can be found in those channels. |
| `b_client_info_view` | Allow the bot to gather client information like client nickname. |
| `i_client_private_textmessage_power` | Allow the bot to send text messages to the client. |
