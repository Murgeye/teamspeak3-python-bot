# About

This plugin extends your bot with the feature to automatically assign a group to clients, which are live on Twitch.

This plugin requires a Twitch account as you need to register this bot as your own application in order to get an API client ID and secret. See [Configuration: Twitch: Register App](#twitch-register-app).


# Available Commands

The following table shows all available arguments for the command `!twitchlive` of this plugin:

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
TwitchLive: twitch_live.main
```


## Options

This plugin supports the following options:

| Option | Default | Description |
| ---: | :---: | :--- |
| `auto_start` | `True` | Either if the plugin should automatically start when the Bot starts and it's configured or not. |
| `enable_dry_run` | `False` | Set to `True`, if you want to test the plugin without executing the actual tasks. Instead it logs what it would have done. |
| `frequency` | `5.0` | The frequency in seconds how often (and fast) the plugin should react (e.g. somebody goes live on twitch, every 5 seconds the bot would notice this and do something). |
| `twitch_live_servergroup_name` | `None` | The name of the servergroup, which should be un-/assigned to clients based on the Twitch stream status. |
| `twitch_api_client_id` | `None` | Your personal Twitch API client ID. See [Configuration: Twitch: Register App](#twitch-register-app). |
| `twitch_api_client_secret` | `None` | Your personal Twitch API client secret. See [Configuration: Twitch: Register App](#twitch-register-app). |

If you need to change some of these default options, simply add them to your `config.ini` under the respective `ModuleName` section:

```
[twitch_live]
frequency: 60.0
twitch_live_servergroup_name: Live@Twitch
twitch_api_client_id: 1ec8e09a145fc972b5eed9d1deb51631
twitch_api_client_secret: ca733c04c302365cc782283ed5b7d39a
```

Please keep in mind, that you need to reload the plugin afterwards. Either by restarting the entire bot or by using a plugin command, if it has one.

Next, you only need to set the link to the Twitch stream as client description for every client, who is streaming via Twitch:

1. **Right-click a client** on your TeamSpeak server
2. Click on **Change description**
3. Set the link to the clients Twitch stream (e.g. `https://www.twitch.tv/MyStream`)
4. Save the change


## Twitch: Register App

To be able to use this plugin, you need to register this bot as an application at Twitch, so that you get API credentials.

Here you can find the detailed official documentation: https://dev.twitch.tv/docs/authentication/register-app

Quick instructions:

1. Login to your Twitch account or sign up for a new one, if you don't have any yet
2. Open https://dev.twitch.tv/console
3. Click on **Applications**
4. Click on **Register your app**
5. Fill out the form:
    - **Name:** `teamspeak3-python-bot` (just an example; use whatever name, which you want - it's only visible on this Twitch page)
    - **OAuth Redirect URLs:** `http://localhost` (not relevant, so simply set this for example)
    - **Category:** `Application Integration` (or `Other`)
6. Afterwards, you will see the `Client-ID` of your application. Set this value for `twitch_api_client_id`.
7. Click on **New secret**. You will temporary see/get the `Client-Secret` of your application. Set this value for `twitch_api_client_secret`.


# Required Permissions

This plugin requires the following permissions on your TeamSpeak server:

| Permission | Explanation |
| ---: | :--- |
| `b_virtualserver_client_list` | Allow the bot to get a list of all connected clients on your virtual server. |
| `i_channel_subscribe_power` | The bot must be able to subscribe channels, so that clients can be found in those channels. |
| `i_group_member_add_power` | The bot will assign clients the specified servergroup, when the Twitch streamer is live. |
| `i_group_member_remove_power` | The bot will unassign clients the specified servergroup, when the Twitch streamer is offline. |
| `i_client_private_textmessage_power` | The bot will send in specific cases a private message to the client. If somebody wants to know the plugin version for example. |
