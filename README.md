# TS3 Bot
Simple Teamspeak 3 bot based on the ts3API located at
https://github.com/Murgeye/ts3API.

# Getting the bot
1. Clone this repository
2. Update the ts3API submodule by running `git submodule update --init --recursive` in the directory created in 1.

# Configuration
You need a configuration file called config.ini in the bots root directory.
config.example.ini should help to get you started with that. The format of the
config file is as follows:

```
[General]
#Nickname of the bot
Botname: ExampleBot
#IP or dns name of the server
Host: 127.0.0.1
#Server query port
Port: 10011 
#Virtual Server id, usually 1 if you are running only one server
ServerId: 1 
#Channel to move the bot to on joining the server
DefaultChannel: Botchannel
#Server Query Login Name
User: serveradmin
#ServerQueryPassword
Password: password

#Configuration for Plugins, each line corresponds to 
#a plugin in the modules folder
[Plugin]
#Format is: ModuleName, python module name
#You can use module paths by using points:
#e.g.: complex_module.example_module => module/complex_module/example_module
#The module name is only used for logging, it can be anything, but not empty
AfkMover: afkmover
UtilCommand: utils
```

# Running the bot
You can run the bot by executing main.py. If you intend to run the bot on boot
you should probably create a bash script that sleeps before starting the bot to 
allow the Teamspeak server to startup first:
```
#!/bin/bash
cd /path/to/bot
sleep 60
./main.py &> output.log
```

# Troubleshooting
## The bot just crashes without any message
Any error messages should be in the file bot.log in the root directory of the bot.
If this file doesn't exist the file permissions of the root directory are probably wrong.

## Something doesn't work
The bot writes quite some logs in the root directory. Check those for errors and open
an issue if the issue remains.