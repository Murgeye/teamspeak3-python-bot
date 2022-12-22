# About

This plugin extends your bot with the feature to automatically create channels for users, which want their own channel with a respective group (e.g. Channel Admin).


# Available Commands

The following table shows all available arguments for the command `!privatechannelmanager` of this plugin:

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
PrivateChannelManager: private_channel_manager.main
```

## Options

This plugin supports the following options:

| Option | Default | Description |
| ---: | :---: | :--- |
| `auto_start` | `True` | Either if the plugin should automatically start when the Bot starts and it's configured or not. |
| `enable_dry_run` | `False` | Set to `True`, if you want to test the plugin without executing the actual tasks. Instead it logs what it would have done. |
| `exclude_servergroups` | `None` | Provide a comma seperated list of servergroup names, which should never get an own channel by the bot. |
| `channel_name` | `Create own private channel` | The channel name, which a client must join to request an own channel. The name can be a pattern. |
| `channel_group_name` | `Channel Admin` | The channel group name, which a client should get assigned in his own channel. |
| `channel_deletion_delay_seconds` | `0` | Time in seconds before this channel will be auto deleted when empty. `0` means immediately. |

If you need to change some of these default options, simply add them to your `config.ini` under the respective `ModuleName` section:

```
[private_channel_manager]
exclude_servergroups: Guest,Bot
channel_name: Create Private Channel
channel_deletion_delay_seconds: 300
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
