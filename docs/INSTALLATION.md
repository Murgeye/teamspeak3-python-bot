# Requirements

- [Git](https://git-scm.com/)
- [Python 3](https://www.python.org/)
  - [pip](https://pip.pypa.io/en/stable/installation/) (usually a part of Python)

# Installation

1. Clone this repository using Git: `git clone https://github.com/Murgeye/teamspeak3-python-bot.git`
2. Switch into the project directory: `cd teamspeak3-python-bot/`
3. Update the Git submodules: `git submodule update --init --recursive`
4. Create a Python virtual env: `python3 -m venv venv`
5. Active the Python virtual env: `source venv/bin/activate`
6. Install the Python dependencies: `pip3 install -r requirements.txt`.
7. Create your own config file: `cp config.example.ini config.ini`
8. Adjust the config file: `vim config.ini` (see [configuration](/docs/CONFIGURATION.md#configuration) for further information)

Instead of setting up the above Python virtual env, you can also skip the steps 4 and 5 and instead install the dependencies globally. However, this is not recommended as you could run other Python projects on the same system, which require then a different version of specific dependencies.

# Running the bot

## Quick Start

The quickest way to start the bot, is to run the following command within the project directory:

```shell
./main
```

You will not see any output, but when you check the `logs/` directory, you should see some log files. The bot should be also connected to your TeamSpeak server. Right now, it's just not doing anything as no plugin is configured yet.

You can stop the bot by aborting the above command using the key combination `Ctrl`+`C`.

## Advanced (recommended)

This way you ensure, that the bot automatically starts when your system boots and that it automatically restarts, when it crashed due to whatever reason.

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

Next, checkout the [configuration](/docs/CONFIGURATION.md).
