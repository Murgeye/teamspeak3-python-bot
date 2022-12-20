# About

This plugin extends your bot with the feature to [...].


# Available Commands

The following table shows all available arguments for the command `!plugintemplate` of this plugin:

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
PluginTemplate: plugin_template.main
```

## Options

This plugin supports the following options:

| Option | Default | Description |
| ---: | :---: | :--- |
| `auto_start` | `True` | Either if the plugin should automatically start when the Bot starts and it's configured or not. |
| `enable_dry_run` | `False` | Set to `True`, if you want to test the plugin without executing the actual tasks. Instead it logs what it would have done. |
| `frequency` | `30.0` | The frequency in seconds how often (and fast) the plugin should react (e.g. somebody sets his own as "AFK", every 30 seconds the bot would notice this and do something). |
| `some_option` | `someDefaultValue` | Some description for this option, what it is responsible for and what could potentially set. |

If you need to change some of these default options, simply add them to your `config.ini` under the respective `ModuleName` section:

```
[plugin_template]
frequency: 10.0
some_option: someChangedValue
```

Please keep in mind, that you need to reload the plugin afterwards. Either by restarting the entire bot or by using a plugin command, if it has one.


# Required Permissions

This plugin requires the following permissions on your TeamSpeak server:

| Permission | Explanation |
| ---: | :--- |
| `b_virtualserver_client_list` | Allow the bot to get a list of all connected clients on your virtual server. |
| `i_channel_subscribe_power` | The bot must be able to subscribe channels, so that clients can be found in those channels. |
| `i_client_private_textmessage_power` | The bot will send in specific cases a private message to the client. If somebody wants to know the plugin version for example. |
