# About

This plugin extends your bot with the feature to [...].


# Available Commands

The following table shows all available commands for this plugin:

| Command | Description |
| ---: | :--- |
| `!startplugintemplate`/`!plugintemplatestart` | Start this plugin |
| `!stopplugintemplate`/`!plugintemplatestop` | Stop this plugin |


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
| `someOption` | `someDefaultValue` | Some description for this option, what it is responsible for and what could potentially set. |

If you need to change some of these default options, simply add them to your `config.ini` under the respective `ModuleName` section:

```
[PluginTemplate]
frequency: 10.0
someOption: someChangedValue
```

Please keep in mind, that you need to reload the plugin afterwards. Either by restarting the entire bot or by using a plugin command, if it has one.


# Required Permissions

This plugin requires the following permissions on your TeamSpeak server:

| Permission | Explanation |
| ---: | :--- |
| `i_client_move_power` | Must be equal or higher than `i_client_needed_move_power` of clients/servergroups, which the bot should be able to move. |
