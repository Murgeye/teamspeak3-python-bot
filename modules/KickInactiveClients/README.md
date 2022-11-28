# About

This plugin extends your bot with the feature to automatically kick clients from the TeamSpeak server, when they are idle since a longer time and you need more free slots for other potential joining clients.


# Available Commands

The following table shows all available commands for this plugin:

| Command | Description |
| ---:   | :--- |
| `!startkickinactiveclients`/`!kickinactiveclientsstart` | Start the plugin |
| `!stopkickinactiveclients`/`!kickinactiveclientsstop` | Stop the plugin |


# Configuration

Enable this plugin by adding the following line under the `Plugins` section to your `config.ini`:

```
[Plugins]
KickInactiveClients: KickInactiveClients.main
```

## Options

This plugin supports the following options:

| Option | Default | Description |
| ---: | :---: | :--- |
| `auto_start` | `True` | Either if the plugin should automatically start when the Bot starts and it's configured or not. |
| `enable_dry_run` | `False` | Set to `True`, if you want to test the plugin without executing the actual tasks. Instead it logs what it would have done. |
| `frequency` | `300.0` | The frequency in seconds how often (and fast) the plugin should react (e.g. somebody is idle, every 300 seconds the bot would notice this and do something). |
| `min_idle_time_seconds` | `7200` | The minimum time in seconds a client must be idle to get kicked from the server. |
| `min_clientsonline_kick_threshold` | `108` | Only start kicking idle clients from the server, when more clients than this value are online. Set this to `0` to always kick idle clients. |
| `kick_reason_message` | `Sorry for kicking, but we need slots!` | The kick reason message, which will be shown the respective kicked client. (Maximum supported length: 40 characters) |

If you need to change some of these default options, simply add them to your `config.ini` under the respective `ModuleName` section:

```
[KickInactiveClients]
frequency: 60.0
min_idle_time_seconds: 3600
min_clientsonline_kick_threshold: 55
```

Please keep in mind, that you need to reload the plugin afterwards. Either by restarting the entire bot or by using a plugin command, if it has one.


# Required Permissions

This plugin requires the following permissions on your TeamSpeak server:

| Permission | Explanation |
| ---: | :--- |
| `b_virtualserver_client_list` | Allows the bot to get all clients on your virtual server. |
| `i_channel_subscribe_power` | Must be equal or higher than `i_channel_needed_subscribe_power` of channels, which the bot should be able to find / see users. |
| `i_client_kick_from_server_power` | Must be equal or higher than `i_client_needed_kick_from_server_power` of clients/servergroups, which the bot should be able to kick. |
