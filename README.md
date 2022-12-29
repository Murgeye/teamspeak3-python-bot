# TeamSpeak Bot

[![Code Style](https://github.com/Sebi94nbg/teamspeak3-python-bot/actions/workflows/black_formatter.yml/badge.svg?branch=main)](https://github.com/Sebi94nbg/teamspeak3-python-bot/actions/workflows/black_formatter.yml?query=branch%3Amain)
[![Python Lint](https://github.com/Sebi94nbg/teamspeak3-python-bot/actions/workflows/pylint.yml/badge.svg?branch=main)](https://github.com/Sebi94nbg/teamspeak3-python-bot/actions/workflows/pylint.yml?query=branch%3Amain)
[![CodeQL](https://github.com/Sebi94nbg/teamspeak3-python-bot/actions/workflows/codeql-analysis.yml/badge.svg?branch=main)](https://github.com/Sebi94nbg/teamspeak3-python-bot/actions/workflows/codeql-analysis.yml?query=branch%3Amain)

Simple TeamSpeak bot based on the [ts3API](https://github.com/Murgeye/ts3API).

Works with a TeamSpeak 3 (TS3) and TeamSpeak 5 (TS5; Beta) server.

# Installation

[Open Installation README](/docs/INSTALLATION.md)

# Configuration

[Open Configuration README](/docs/CONFIGURATION.md)

# Available Plugins

All existing functionality is based on plugins.

| Plugin | Readme |
| ---:   | :--- |
| utils | [Open documentation](#utils) |
| quotes | [Open documentation](#quotes) |
| afk_mover | [Open documentation](/modules/afk_mover/README.md) |
| idle_mover | [Open documentation](/modules/idle_mover/README.md) |
| kick_inactive_clients | [Open documentation](/modules/kick_inactive_clients/README.md) |
| bad_nickname | [Open documentation](/modules/bad_nickname/README.md) |
| twitch_live | [Open documentation](/modules/twitch_live/README.md) |
| channel_manager | [Open documentation](/modules/channel_manager/README.md) |
| private_channel_manager | [Open documentation](/modules/private_channel_manager/README.md) |
| switch_supporter_channel_status | [Open documentation](/modules/switch_supporter_channel_status/README.md) |
| inform_team_about_newbie | [Open documentation](/modules/inform_team_about_newbie/README.md) |

Also see the [configuration](#configuration) section for further details regarding configuration.

# Text Commands

The bot supports text commands, which are added via plugins (see [Available Plugins](#available-plugins)).

Each plugin documentation provides further information about each command.

## Utils

This plugin extends your bot with various commands.

### Available Commands

The following table shows all available commands for this plugin:

| Command | Description |
| ---:   | :--- |
| `!version` | Answer with the current module version |
| `!stop` | Stop the bot (you need to start it afterwards manually) |
| `!restart`/`!reload` | Restart the bot to e.g. reload the configuration. |
| `!help`/`!commands`/`!commandlist` | Returns the list of available bot commands. |
| `!multimove "fromChannel" "toChannel"` | Moves all users from all, one or multiple channels to a specific target channel. See `!multimove` for further possibilities. |

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

### Available Commands

The following table shows all available arguments for the command `!addquote` of this plugin:

| Argument | Description |
| ---:   | :--- |
| `<quote>` | Adds the new quote `<quote>`. |

### Configuration

Enable this plugin by adding the following line under the `Plugins` section to your `config.ini`:

```
[Plugins]
Quotes: quotes
```

#### Options

This plugin does not support any options.

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

# Writing plugins

[Open Plugins README](/docs/PLUGINS.md)

# Troubleshooting

[Open Troubleshooting README](/docs/TROUBLESHOOTING.md)
 