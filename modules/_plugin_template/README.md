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
PluginTemplate: _plugin_template.plugin_template
```

## Options

This plugin supports the following options:

| Option | Default | Description |
| ---: | :---: | :--- |
| `someOption` | `someValue` | Some description for this option, what it is responsible for and what could potentially set. |

If you need to change some of these default options, simply add them to your `config.ini` under the respective `ModuleName` section:

```
[PluginTemplate]
someOption: someChangedValue
```

Please keep in mind, that you need to reload the plugin afterwards. Either by restarting the entire bot or by using a plugin command, if it has one.
