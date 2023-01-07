# About

This plugin extends your bot with the feature to automatically create channels for users, which request an own channel.
Depending on your personal configuration, these channels will be automatically cleaned up (deleted) again once they are
empty - either immediately or after a specific amount of seconds.

Configure for example a "Support Lobby", where clients will get an own channel, when they join the lobby. Or define a
"Create Private Channel" channel and every client, which joins this channel will get an own channel with e.g. "Channel
Admin" permissions.


# Available Commands

The following table shows all available arguments for the command `!channelrequester` of this plugin:

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
ChannelRequester: channel_requester.main
```

## Options

This plugin supports the following general options:

| Option | Default | Description |
| ---: | :---: | :--- |
| `auto_start` | `True` | Either if the plugin should automatically start when the Bot starts and it's configured or not. |
| `enable_dry_run` | `False` | Set to `True`, if you want to test the plugin without executing the actual tasks. Instead it logs what it would have done. |
| `exclude_servergroups` | `None` | Provide a comma seperated list of servergroup names, which should never get an own channel by the bot. |

This plugin supports the following channel options:

> **_NOTE:_** `<alias>` can be anything - it's only used to differentiate between multiple channel configurations. Supported characters for the `alias`: `a-z`, `A-Z`, `0-9_`

| Option | Default | Description |
| ---: | :---: | :--- |
| `<alias>.main_channel_name` | `None` | The channel name, which a client must join to request an own channel. The name can be a pattern. |
| `<alias>.channel_name` | `%u` | How the requested channel should be initially named. A channel name must be unique! Supported variables: `%i` (counting integer number: 1, 2, 3, ...), `%u` (the clients nickname) |
| `<alias>.channel_group_name` | `Channel Admin` | The channel group name, which a client should get assigned in his own channel. |
| `<alias>.<channel_property>` | `None` | Optionally set any officially available channel property like `channel_description` or `channel_maxclients`. |
| `<alias>.<channel_permission_name>` | `None` | Optionally set any officially available channel permission name like `i_channel_needed_join_power` or `i_ft_needed_file_browse_power`. |

If you need to change some of these default options, simply add them to your `config.ini` under the respective `ModuleName` section:

```
[channel_requester]
exclude_servergroups: Guest,Bot

support.main_channel_name: Support Lobby
support.channel_name: Support %i
support.channel_group_name: Guest
support.channel_maxclients: 2

private_channels.main_channel_name: Create Private Channel
private_channels..channel_name: Kingdom of %u
private_channels.channel_delete_delay: 300
private_channels.i_ft_needed_file_browse_power: 75
```

Please keep in mind, that you need to reload the plugin afterwards. Either by restarting the entire bot or by using a plugin command, if it has one.


# Required Permissions

This plugin requires the following permissions on your TeamSpeak server:

| Permission | Explanation |
| ---: | :--- |
| `b_virtualserver_notify_register` | Allow the bot to register for specific events. |
| `b_client_info_view` | Allow the bot to gather client information like client nickname. |
| `b_virtualserver_channel_search` | Allow the bot to search for a channel based on a name pattern. |
| `b_virtualserver_channelgroup_list` | Allow the bot to list all channelgroups to find to respective channel group, which should get assigned to clients. |
| `b_virtualserver_servergroup_list` | Allow the bot list all servergroups to be able to exclude clients. |
| `i_channel_modify_power` | Allow the bot to modify the recently created channel. |
| `b_channel_modify_make_temporary` | Allow the bot to modify the recently created channel to make it temporary. |
| `b_channel_create_child` | Allow the bot to create child channels. |
| `b_channel_create_semi_permanent` | Allow the bot to create semi-permanent channels. |
| `b_channel_create_temporary` | Allow the bot to create temporary channels. |
| `i_group_member_add_power` | Allow the bot to add the respective clients to the respective channel group. |
| `i_client_move_power` | Allow the bot to move the respective clients into their private channel. |
| `i_client_private_textmessage_power` | Allow the bot to send text messages to the client. |
