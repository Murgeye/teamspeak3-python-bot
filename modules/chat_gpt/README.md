# About

This plugin extends your bot with the feature of an intelligent chatbot, called ChatGPT.

TeamSpeak clients can write ChatGPT a private textmessage and will receive a reply from ChatGPT.

This plugin requires an OpenAI account as you need an API key. See [Configuration: OpenAI: Create API Key](#openai-create-api-key).


# Available Commands

The following table shows all available arguments for the command `!chatgpt` of this plugin:

| Argument | Description |
| ---:   | :--- |
| `version` | Sends a text message with the version of this plugin. |
| `start` | Start this plugin |
| `stop` | Stop this plugin |
| `restart` | Restarts this plugin |
| `ask <your question/text>` | Sends a text to ChatGPT and returns its reponse to the client. |


# Configuration

Enable this plugin by adding the following line under the `Plugins` section to your `config.ini`:

```
[Plugins]
ChatGPT: chat_gpt.main
```


## Options

This plugin supports the following options:

| Option | Default | Description |
| ---: | :---: | :--- |
| `auto_start` | `True` | Either if the plugin should automatically start when the Bot starts and it's configured or not. |
| `enable_dry_run` | `False` | Set to `True`, if you want to test the plugin without executing the actual tasks. Instead it logs what it would have done. |
| `openai_api_key` | `None` | Your personal OpenAI API key. See [Configuration: OpenAI: Create API Key](#openai-create-api-key). |

If you need to change some of these default options, simply add them to your `config.ini` under the respective `ModuleName` section:

```
[chat_gpt]
openai_api_key: mm-4Qgt3cxJEAf6bnmPTWTSchD8gjgXffz4QeeLy4XSxbnZZsLA
```

Please keep in mind, that you need to reload the plugin afterwards. Either by restarting the entire bot or by using a plugin command, if it has one.


## OpenAI: Create API Key

To be able to use this plugin, you need an API key from OpenAI.

Instructions:

1. Login to your OpenAI account or sign up for a new one, if you don't have any yet: https://platform.openai.com
2. Click on your profile in the right top corner and select **View API keys**
3. Click on **Create new secret key**
4. Now you will see your personal secret API key. Set this value for `openai_api_key`.


# Required Permissions

This plugin requires the following permissions on your TeamSpeak server:

| Permission | Explanation |
| ---: | :--- |
| `i_client_private_textmessage_power` | The bot will send the ChatGPT response as a private message to the client. |
