# Troubleshooting

## The bot just crashes without any message

Any error messages should be in the log files under `logs/` within the root directory of the bot.

If this file doesn't exist the permissions of the root directory are probably wrong.

## The bot connects but I cannot see it.

First, make sure that you have set up the server permissions correctly as mentioned in the
[Permissions](/docs/CONFIGURATION.md#permissions) section. In addition to this, you might have to enable the
"Show ServerQuery Clients" setting in your TeamSpeak client under Bookmarks->Manage Bookmarks
and reconnect to the server. You might have to enable advanced settings for this.

![Show Serverquery Setting](/images/show_serverquery.png)

If you still cannot see the bot after reconnecting, check if the bot is really still connected
by checking the logs of both the bot and the server. If you cannot find the problem, feel free
to open a new issue.

## The bot does not react to commands.

The bot can only handle commands via direct message. If you are sending a direct message and the bot still
does not react, try setting the permissions as mentioned in the [Permissions](/docs/CONFIGURATION.md#permissions) section.

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
