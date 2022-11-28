# TS3 Bot

Simple TeamSpeak 3 bot based on the [ts3API](https://github.com/Murgeye/ts3API).

# Requirements

- Git
- Python 3

# Installation

1. Clone this repository using Git: `git clone https://github.com/Murgeye/teamspeak3-python-bot.git`
2. Switch into the project directory: `cd teamspeak3-python-bot/`
3. Update the ts3API submodule(s): `git submodule update --init --recursive`
4. Install the Python dependencies: `pip3 install -r requirements.txt`.
5. Create your own config file: `cp config.example.ini config.ini`

# Configuration

Edit the `config.ini` to your requirements. Set the correct TeamSpeak host, port, serverquery credentials etc..

## Section: General

This section contains general settings for the Bot:

| Option | Type    | Description |
| ---:   | :---: | :--- |
| Botname | string | The client nickname of your Bot. Will be visible to other clients. |
| Host | string | The IP address or FQDN of your TeamSpeak server. |
| Port | integer | The ServerQuery port of your TeamSpeak server. |
| SSH | boolean | Whether the ServerQuery port is the SSH port or not. |
| AcceptAllSSHKeys | boolean | Whether to accept any SSH key or not. |
| SSHHostKeyFile | string | The path to a SSH host key file. |
| SSHLoadSystemHostKeys | boolean | Whether to load system host keys or not. |
| ServerId | integer | The virtualserver ID to connect to. |
| DefaultChannel | string | The name of the channel, where the Bot should be in. Can be a pattern. |
| User | string | The ServerQuery user to authenticate with. |
| Password | string | The password for the ServerQuery user. |

## Section: Plugins

This section contains plugin settings for the Bot.

You can enable plugins by adding each respective plugin as an extra line into this section:

- Simple plugins: `ModuleName: PythonModuleName`
- Complex plugins: `ModuleName: complex_module.example_module => module/complex_module/example_module`

The `ModuleName` is only used for logging and can be anything, but not empty.

If a plugin supports any kind of configuration, you need to edit the respective Python script of the plugin (e.g. `modules/afkmover.py`).

# Running the bot

The following instructions were tested on Linux Debian 11 (Bullseye).

1. Create a Linux user: `useradd tsbot`
2. Copy the `tsbot.defaults` file from this repository to the following path: `/etc/default/tsbot`
3. Ensure, that the permissions are correct:
   - `sudo chown root:root /etc/default/tsbot`
   - `sudo chmod 0644 /etc/default/tsbot`
4. Adjust the defaults config file, if necessary: `vim /etc/default/tsbot`
5. Copy the `tsbot.service` file from this repository to the following path: `/etc/systemd/system/tsbot.service`
6. Ensure, that the permissions are correct:
   - `sudo chown root:root /etc/systemd/system/tsbot.service`
   - `sudo chmod 0777 /etc/systemd/system/tsbot.service`
7. Adjust the following systemd unit options, if necessary:
   - `After`: Add your TeamSpeak server systemd unit, when it is running on the same server as systemd unit.
   - `WorkingDirectory`: Set the correct path to this project directory on your system.
8. Reload systemd: `sudo systemctl daemon-reload`
9. Enable the systemd unit: `sudo systemctl enable tsbot.service`
10. Start the systemd unit: `sudo systemctl start tsbot.service`

Further commands:

- Stop bot: `systemctl stop tsbot.service`
- Restart bot: `systemctl restart tsbot.service`

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

## Permissions

If you want your users to be able to see and message the bot, you will have to change
some server permission - either for specific clients or for server groups:

- `i_client_serverquery_view_power`: Set it to 100 if you want a client/group to be able to see the bot
- `i_client_private_textmessage_power`: Set it to 100 if you want a client/group to be able to write textmessages (and therefore commands) to the bot

Alternatively, you could modify the needed power for both permissions for the ServerQuery.

To see these permission settings you have to enable advanced permissions under `Tools->Options` in your client.

![Show Advanced Permissions](advanced_permissions.png)

## Using SSH (Encrypted ServerQuery connection)

Since server version 3.3 TeamSpeak supports encrypted ServerQuery clients, which should be preferred.

To archive this the connection is wrapped inside a SSH connection. As SSH needs a way to check the host RSA
key, four config options were added:

* SSH: `[y/n/True/False/0/1]` Enables SSH connections (do not forget to enable it on the server
and change the port as well)
* AcceptAllSSHKeys: `[y/n/True/False/0/1]` Accept all RSA host keys
* SSHHostKeyFile: File to save/load host keys to/from
* SSHLoadSystemHostKeys: `[y/n/True/False/0/1]` Load system wide host keys

To add your host key the following workflow is easiest:

1. Activate AcceptAllHostKeys and set a SSHHostKeyFile
2. Connect to the server
3. The servers host key is automatically added to the file
4. Deactivate AcceptAllHostKeys

# Available Plugins

All existing functionality is based on plugins.

| Plugin | Readme |
| ---:   | :--- |
| Utils | [Open documentation](#utils) |
| Quotes | [Open documentation](#quotes) |
| AfkMover | [Open documentation](/modules/AfkMover/README.md) |
| IdleMover | [Open documentation](/modules/IdleMover/README.md) |
| KickInactiveClients | [Open documentation](/modules/KickInactiveClients/README.md) |

# Text Commands

All of the text commands are added via plugins (see the next section).

## Utils

This plugin extends your bot with administrative features via your TeamSpeak server client.

The following table shows all available commands for this plugin:

| Command | Description |
| ---:   | :--- |
| `!hello` | Answers with a message depending on the server group (Server Admin, Moderator, Normal) |
| `!stop` | Stop the bot (you need to start it afterwards manually) |
| `!restart` | Restart the bot |
| `!multimove fromChannel toChannel` | Moves all users from `fromChannel` to `toChannel` (should work for channels containing spaces, most of the time)
| `!kickme` | Kick yourself from the server. |
| `!whoami` | Fun command. |
| `!version` | Answer with the current module version |

## Quotes

This plugin extends your bot with quotes, which get randomly sent to random clients.

The following table shows all available commands for this plugin:

| Command | Description |
| ---:   | :--- |
| `!addquote quote` | Adds the new quote `quote` |

# Writing plugins

A feature of this bot is that it is easily extendable.

To write your own plugin you need to do the following things:

1. Copy the `plugin_template` plugin and name the folder as descriptive as possible for your plugin
2. Update the template Python script to your needs
3. Update and fill the `README.md` within your plugin folder
4. Optionally link your plugin in the main `README.md` of this project under `Available Plugins`, if you are planning to publish it
2. Add your new plugin to the `config.ini`

That's it. The plugin sends regulary a "Hello World!" message to all connected clients. You can build up on that.

You can see some example plugins in the directory modules.

Please check the [ts3API](https://github.com/Murgeye/teamspeak3-python-api) documentation for available API functions, properties, error handling etc..

## Adding setup and exit methods

Upon loading a plugin the ModuleLoader calls any method marked as `@setup` in the plugin.

```
from Moduleloader import *

@setup
def setup_module(ts3bot):
  #Do something, save the bot reference, etc
  pass
```

Upon unloading a module (usually if the bot is closed etc) the ModuleLoader calls any method
marked as `@exit` in the plugin.

```
@exit
def exit_module():
  #Do something, save your state, etc
  pass
```

## Adding a text command

You can register your plugin to specific commands (starting with !) send via private message
by using the `@command` decorator.

The following code example registers the `test_command` function for the command `!test1` and `!test2`:

```
@command('test1','test2',)
@group('Server Admin',)
def test_command(sender, msg):
  print("test")
```

You can register a function for as many commands as you want and you can register as many functions for a command as you want.

The `sender` argument is the client id of the user who sent the command and `msg` contains the whole text
of the private message.

### `@group`

The `@group` decorator specifies which Server Groups are allowed to use this function via textcommands.

You can use regex here so you can do things like `@group('.*Admin.*','Moderator',)` to allow all groups containing the word `Admin` and the `Moderator` group to send this command.

`@group('.*')` allows everybody to use a command. If you don't use `@group` the default will be to allow access to 'Server Admin' and 'Moderator'.

## Listening for events

You can register a function in your plugin to listen for specific server events by using the `@event` decorator.

The following code snippet registers the `inform_enter` function as a listener for the `Events.ClientEnteredEvent`:

```
import ts3API.Events as Events
# ...
@event(Events.ClientEnteredEvent,)
def inform_enter(event):
  print("Client with id " + event.client_id + " left.")
```

You can register a function for multiple events by passing a list of event types to the decorator. To learn more about the events look at the ts3API.Events module.

# Troubleshooting

## The bot just crashes without any message

Any error messages should be in the log files under `logs/` within the root directory of the bot.

If this file doesn't exist the permissions of the root directory are probably wrong.

## The bot connects but I cannot see it.

First, make sure that you have set up the server permissions correctly as mentioned in the
[Permissions](#permissions) section. In addition to this, you might have to enable the
"Show ServerQuery Clients" setting in your TeamSpeak client under Bookmarks->Manage Bookmarks
and reconnect to the server. You might have to enable advanced settings for this.

![Show Serverquery Setting](show_serverquery.png)

If you still cannot see the bot after reconnecting, check if the bot is really still connected
by checking the logs of both the bot and the server. If you cannot find the problem, feel free
to open a new issue.

## The bot does not react to commands.

The bot can only handle commands via direct message. If you are sending a direct message and the bot still
does not react, try setting the permissions as mentioned in the [Permissions](#permissions) section.

## The bot always loses connection after some time.

Your `query_timeout` parameter in the `ts3server.ini` file is probably very low (<10 seconds).

Please set it to a higher value or `0` (this disables the query timeout). If this does not fix
it, feel free to open an issue, there might still be some unresolved problems here.

## The Bot gets banned from our server!

You need to whitelist the IP the bot is connecting from in the Teamspeak configuration file. To do this
change the file `query-ip-whitelist.txt` in the server directory and add a new line with the IP of your bot.

## Something doesn't work

The bot writes quite some logs in the root directory. Check those for errors and open an issue if the issue remains.

## The bot stopped working after I updated my server!

Update the bot! Server version 3.4.0 changed the way the query timeout was handled.

Versions of the bot older then 17. September 2018 will not work correctly.
