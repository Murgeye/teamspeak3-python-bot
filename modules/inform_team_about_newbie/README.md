# About

This plugin extends your bot with the feature to automatically poke your team, when a newbie joins the server. Optionally, this newbie can be automatically moved into a support channel.


# Available Commands

The following table shows all available arguments for the command `!informteamaboutnewbie` of this plugin:

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
InformTeamAboutNewbie: inform_team_about_newbie.main
```

## Options

This plugin supports the following options:

| Option | Default | Description |
| ---: | :---: | :--- |
| `auto_start` | `True` | Either if the plugin should automatically start when the Bot starts and it's configured or not. |
| `enable_dry_run` | `False` | Set to `True`, if you want to test the plugin without executing the actual tasks. Instead it logs what it would have done. |
| `newbie_servergroup_name` | `Guest` | The servergroup name, which newbies have. |
| `support_channel_name` | `None` | Optionally define the name of your support channel, where newbies should be automatically moved into, when they join your server. |
| `team_servergroup_names` | `Moderator` | A comma-seperated list of servergroup names of your team, which should be poked when a newbie joined the server. |
| `newbie_poke_message` | `Hello %u! A team member will welcome you in a moment.` | The poke message, which will be sent to the newbie. Supported variables: `%u` (the clients nickname, which receives the poke message) (Max. poke message length is 100 characters.) |
| `team_poke_message` | `Hello %u! The following newbie joined: %n` | The poke message, which will be sent to all team clients. Supported variables: `%c` (count of team members, which will be poked), `%n` (the newbies nickname), `%u` (the clients nickname, which receives the poke message) (Max. poke message length is 100 characters.) |

If you need to change some of these default options, simply add them to your `config.ini` under the respective `ModuleName` section:

```
[inform_team_about_newbie]
newbie_servergroup_name: Newbie
support_channel_name: Support
team_servergroup_names: Moderator,Supporter
team_poke_message: The following newbie is waiting for an introduction: %n
```

Please keep in mind, that you need to reload the plugin afterwards. Either by restarting the entire bot or by using a plugin command, if it has one.


# Required Permissions

This plugin requires the following permissions on your TeamSpeak server:

| Permission | Explanation |
| ---: | :--- |
| `b_virtualserver_notify_register` | Allow the bot to register for specific events. |
| `b_virtualserver_servergroup_list` | Allow the bot list all servergroups to be able to exclude clients. |
| `b_virtualserver_channel_search` | Allow the bot to search for a channel based on a name pattern. |
| `i_client_move_power` | Allow the bot to move the respective clients into their private channel. |
| `b_virtualserver_servergroup_client_list` | Allow the bot to get a list of clients of your servergroups. |
| `b_virtualserver_client_list` | Allow the bot to get a list of current connected clients. |
| `i_channel_subscribe_power` | Allow the bot to subscribe to channels, where it should be able to find clients using the `clientlist` command. |
| `i_client_poke_power` | Allow the bot to poke the newbie and respective team members. |
| `i_client_private_textmessage_power` | Allow the bot to send text messages to the client. |
