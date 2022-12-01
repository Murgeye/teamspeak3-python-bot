# About

This plugin extends your bot with the feature to automatically move clients to an AFK channel, when they are idle for a specific amount of time.


# Available Commands

The following table shows all available commands for this plugin:

| Command | Description |
| ---:   | :--- |
| `!idlemover version` | Sends a text message with the version of this plugin. |
| `!idlemover start` | Start this plugin |
| `!idlemover stop` | Stop this plugin |
| `!idlemover restart` | Restarts this plugin |


# Configuration

Enable this plugin by adding the following line under the `Plugins` section to your `config.ini`:

```
[Plugins]
IdleMover: IdleMover.main
```

## Options

This plugin supports the following options:

| Option | Default | Description |
| ---: | :---: | :--- |
| `auto_start` | `True` | Either if the plugin should automatically start when the Bot starts and it's configured or not. |
| `enable_dry_run` | `False` | Set to `True`, if you want to test the plugin without executing the actual tasks. Instead it logs what it would have done. |
| `frequency` | `30.0` | The frequency in seconds how often (and fast) the plugin should react (e.g. somebody is idle, every 30 seconds the bot would notice this and do something). |
| `auto_move_back` | `True` | Either if clients, which are no longer idle should be moved back to their original channel or not. |
| `min_idle_time_seconds` | `600` | The minimum time in seconds a client must be idle to get moved to the channel `channel`. |
| `resp_channel_settings` | `True` | Either if the channel settings like max. clients and password should be respected or not, even when the ServerQuery user could ignore them. |
| `fallback_channel` | `None` | Either to move a client, which could not be moved to the old channel due to an error (e.g. channel does not exist anymore or is full) to a different channel (provide the channel name pattern here) or leave him in the `channel` (set to `None`). |
| `channel` | `AFK` | The name of your AFK channel, where clients should be moved to while they are idle. |

If you need to change some of these default options, simply add them to your `config.ini` under the respective `ModuleName` section:

```
[IdleMover]
frequency: 60.0
min_idle_time_seconds: 300
channel: Away
```

Please keep in mind, that you need to reload the plugin afterwards. Either by restarting the entire bot or by using a plugin command, if it has one.


# Required Permissions

This plugin requires the following permissions on your TeamSpeak server:

| Permission | Explanation |
| ---: | :--- |
| `b_virtualserver_client_list` | Allows the bot to get all clients on your virtual server. |
| `i_channel_subscribe_power` | Must be equal or higher than `i_channel_needed_subscribe_power` of channels, which the bot should be able to find / see users. |
| `i_client_move_power` | Must be equal or higher than `i_client_needed_move_power` of clients/servergroups, which the bot should be able to move. |
