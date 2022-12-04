# Configuration

Edit the `config.ini` to your requirements. Set the correct TeamSpeak host, port, serverquery credentials etc..

The INI file has different sections. The start of a section is defined by `[SectionName]`. All configuration options below this section belong to this section until the next section is defined.

## Section: General

This section contains general settings for the Bot:

| Option | Default | Type    | Description |
| ---:   | :---: | :---: | :--- |
| Botname | `ExampleBot` | string | The client nickname of your Bot. Will be visible to other clients. |
| Host | `127.0.0.1` | string | The IP address or FQDN of your TeamSpeak server. |
| Port | `10022` | integer | The ServerQuery port of your TeamSpeak server. |
| SSH | `True` | boolean | Whether the ServerQuery port is the SSH port or not. |
| AcceptAllSSHKeys | `True` | boolean | Whether to accept any SSH key or not. |
| SSHHostKeyFile | `.ssh/ssh_hostkeys` | string | The path to a SSH host key file. |
| SSHLoadSystemHostKeys | `False` | boolean | Whether to load system host keys or not. |
| ServerId | `1` | integer | The virtualserver ID to connect to. |
| DefaultChannel | `Botchannel` | string | The name of the channel, where the Bot should be in. Can be a pattern. |
| User | `serveradmin` | string | The ServerQuery user to authenticate with. |
| Password | `query-password` | string | The password for the ServerQuery user. |

### Using SSH (Encrypted ServerQuery connection)

Since the TeamSpeak server version 3.3 TeamSpeak supports encrypted ServerQuery clients. It's recommend to use SSH.

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

## Section: Plugins

This section contains plugin settings for the Bot.

You can enable plugins by adding each respective plugin as an extra line into this section:

- Simple plugins: `ModuleName: PythonModuleName`
- Complex plugins: `ModuleName: plugin_template.main => module/plugin_template/`

The `ModuleName` is only used for logging and can be anything, but not empty.

`PythonModuleName` or `plugin_template.main` must be the file path to the respective Python script, which should be loaded (without the file extension `.py` and with `.` instead of `/`).

Some plugins support configurations to customize them for your personal needs. There, please check the respective plugin documentation.

## Permissions

If you want your users to be able to see and message the bot, you will have to change some server permission - either for specific clients or for server groups:

- `i_client_serverquery_view_power`: Set it to 100 if you want a client/group to be able to see the bot
- `i_client_private_textmessage_power`: Set it to 100 if you want a client/group to be able to write textmessages (and therefore commands) to the bot

Alternatively, you could modify the needed power for both permissions for the ServerQuery.

To see these permission settings you have to enable advanced permissions under `Tools->Options` in your client.

![Show Advanced Permissions](/images/advanced_permissions.png)
