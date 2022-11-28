# About

This plugin extends your bot with the feature to automatically move clients to an AFK channel, when they are idle for a specific amount of time.


# Available Commands

The following table shows all available commands for this plugin:

| Command | Description |
| ---:   | :--- |
| `!startidle`/`!idlestart`/`!idlemove` | Start the idle mover |
| `!stopidle`/`!idlestop` | Stop the idle mover |


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
