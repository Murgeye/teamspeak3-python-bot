# About

This plugin extends your bot with the feature to automatically kick clients from the TeamSpeak server, when they are using a client nickname, which is not allowed.


# Available Commands

The following table shows all available arguments for the command `!badnickname` of this plugin:

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
BadNickname: BadNickname.main
```

## Options

This plugin supports the following options:

| Option | Default | Description |
| ---: | :---: | :--- |
| `auto_start` | `True` | Either if the plugin should automatically start when the Bot starts and it's configured or not. |
| `enable_dry_run` | `False` | Set to `True`, if you want to test the plugin without executing the actual tasks. Instead it logs what it would have done. |
| `frequency` | `30.0` | The frequency in seconds how often (and fast) the plugin should react (e.g. somebody uses a not allowed nickname, every 30 seconds the bot would notice this and do something). |
| `exclude_servergroups` | `None` | Provide a comma seperated list of servergroup names, which should never get kicked by the bot. |
| `name_pattern` | `[a|4]dm[i|1]n` | A [regular expression](https://docs.python.org/3/library/re.html), which client nicknames are not allowed. (case insensitive) |
| `kick_reason_message` | `Your client nickname is not allowed here!` | The kick reason message, which will be shown the respective kicked client. (Maximum supported length: 40 characters) |

If you need to change some of these default options, simply add them to your `config.ini` under the respective `ModuleName` section:

```
[BadNickname]
frequency: 10.0
exclude_servergroups: Server Admin,Bot
name_pattern: [a|4]dm[i|1]n[i|1][s|5][tr][a|4][t][o|0][r]?
kick_reason_message: Please reconnect with a different nickname.
```

Please keep in mind, that you need to reload the plugin afterwards. Either by restarting the entire bot or by using a plugin command, if it has one.


# Required Permissions

This plugin requires the following permissions on your TeamSpeak server:

| Permission | Explanation |
| ---: | :--- |
| `b_virtualserver_client_list` | Allows the bot to get all clients on your virtual server. |
| `i_channel_subscribe_power` | Must be equal or higher than `i_channel_needed_subscribe_power` of channels, which the bot should be able to find / see users. |
| `i_client_kick_from_server_power` | Must be equal or higher than `i_client_needed_kick_from_server_power` of clients/servergroups, which the bot should be able to kick. |
