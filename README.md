# TS3 Bot

Simple TeamSpeak 3 bot based on the [ts3API](https://github.com/Murgeye/ts3API).

# Installation

[Open Installation README](/docs/INSTALLATION.md)

# Configuration

[Open Configuration README](/docs/CONFIGURATION.md)

# Available Plugins

All existing functionality is based on plugins.

| Plugin | Readme |
| ---:   | :--- |
| Utils | [Open documentation](#utils) |
| Quotes | [Open documentation](#quotes) |
| AfkMover | [Open documentation](/modules/AfkMover/README.md) |
| IdleMover | [Open documentation](/modules/IdleMover/README.md) |
| KickInactiveClients | [Open documentation](/modules/KickInactiveClients/README.md) |
| BadNickname | [Open documentation](/modules/BadNickname/README.md) |
| TwitchLive | [Open documentation](/modules/TwitchLive/README.md) |

Also see the [configuration](#configuration) section for further details regarding configuration.

# Text Commands

The bot supports text commands, which are added via plugins (see [Available Plugins](#available-plugins)).

Each plugin documentation provides further information about each command.

## Utils

This plugin extends your bot with administrative features via your TeamSpeak server client.

### Available Commands

The following table shows all available commands for this plugin:

| Command | Description |
| ---:   | :--- |
| `!version` | Answer with the current module version |
| `!stop` | Stop the bot (you need to start it afterwards manually) |
| `!restart`/`!reload` | Restart the bot to e.g. reload the configuration. |
| `!help`/`!commands`/`!commandlist` | Returns the list of available bot commands. |
| `!multimove "fromChannel" "toChannel"`/`!mm "fromChannel" "toChannel"` | Moves all users from `fromChannel` to `toChannel`. See `!multimove` for further possibilities. |

### Configuration

Enable this plugin by adding the following line under the `Plugins` section to your `config.ini`:

```
[Plugins]
Utils: utils
```

#### Options

This plugin supports the following options:

| Option | Default | Description |
| ---: | :---: | :--- |
| `enable_dry_run` | `False` | Set to `True`, if you want to test the plugin without executing the actual tasks. Instead it logs what it would have done. |

If you need to change some of these default options, simply add them to your `config.ini` under the respective `ModuleName` section:

```
[utils]
enable_dry_run: True
```

Please keep in mind, that you need to reload the plugin afterwards. Either by restarting the entire bot or by using a plugin command, if it has one.

## Quotes

This plugin extends your bot with quotes, which get randomly sent to random clients.

The following table shows all available commands for this plugin:

| Command | Description |
| ---:   | :--- |
| `!addquote quote` | Adds the new quote `quote` |

# Logging

The bot has a `logs/` directory inside the project directory. There you will find multiple log files - one per enabled plugin/feature:

```shell
tsbot@linux:/usr/local/bin/teamspeak3-python-bot$ ls -lh logs/
total 64K
-rw-r--r-- 1 tsbot users 14K Nov 28 00:50 afkmover.log
-rw-r--r-- 1 tsbot users  96 Nov 28 00:46 bot.log
-rw-r--r-- 1 tsbot users  64 Nov 28 00:46 commandhandler.log
-rw-r--r-- 1 tsbot users  62 Nov 28 00:46 eventhandler.log
-rw-r--r-- 1 tsbot users 14K Nov 28 00:50 idlemover.log
-rw-r--r-- 1 tsbot users 16K Nov 28 00:50 kickinactiveclients.log
-rw-r--r-- 1 tsbot users 837 Nov 28 00:46 moduleloader.log
```

Using the environment variable `LOG_LEVEL`, you can change the log level to get either more or less logging output.

# Writing plugins

[Open Plugins README](/docs/PLUGINS.md)

# Troubleshooting

[Open Troubleshooting README](/docs/TROUBLESHOOTING.md)
 