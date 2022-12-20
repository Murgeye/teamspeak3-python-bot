# Requirements

Hardware (minimum):

> **Note**
>
> Depending on the used plugins for this bot and the size of your TeamSpeak server (amount of channels, clients, etc.), you might need more CPU cores and/or memory.

- 1 CPU Core
- 128 MB Memory

Software:

- [Git](https://git-scm.com/)
- [Python 3](https://www.python.org/)
  - [venv](https://docs.python.org/3/library/venv.html) (usually an extra package)
  - [pip](https://pip.pypa.io/en/stable/installation/) (usually a part of Python)

# Installation

1. Install the software requirements from above (e.g. `sudo apt install git python3 python3-venv`)
2. Clone this repository using Git: `git clone https://github.com/Murgeye/teamspeak3-python-bot.git`
3. Switch into the project directory: `cd teamspeak3-python-bot/`
4. Update the Git submodules: `git submodule update --init --recursive`
5. Create your own config file: `cp config.example.ini config.ini`
6. Adjust the config file: `vim config.ini` (see [configuration](/docs/CONFIGURATION.md#configuration) for further information)

Instead of setting up the above Python virtual env, you can also skip the steps 4 and 5 and instead install the dependencies globally. However, this is not recommended as you could run other Python projects on the same system, which require then a different version of specific dependencies.

# Running the bot

## Quick Start

First of all, you should set up a Python virtual environment and install the dependencies:

```shell
python3 -m venv venv
```

```shell
source venv/bin/activate
```

```shell
pip3 install -r requirements.txt
```

Then, simply start the bot:

```shell
./main
```

You will not see any output, but when you check the `logs/` directory, you should see some log files. The bot should be also connected to your TeamSpeak server. Right now, it's just not doing anything as no plugin is configured yet.

You can stop the bot by aborting the above command using the key combination `Ctrl`+`C`.

If you want to run it like this, simply run the following command to put the process into the background:

```shell
./main &
```

## Advanced (recommended)

This way you ensure, that the bot automatically starts when your system boots and that it automatically restarts, when it crashed due to whatever reason.

The following instructions were tested on Linux Debian 11 (Bullseye).

1. Create a Linux user: `useradd tsbot`
2. Install the `teamspeak-bot.service` file from this repository: `cp teamspeak-bot.service /etc/systemd/system/`
3. Ensure, that the permissions are correct:
   - `sudo chown root:root /etc/systemd/system/teamspeak-bot.service`
   - `sudo chmod 0777 /etc/systemd/system/teamspeak-bot.service`
4. Adjust the following systemd unit options, if necessary:
   - `User`: The user, under which your bot should run (see step 1).
   - `Group`: The group, under which your bot should run (see step 1).
   - `After`: Add your TeamSpeak server systemd unit, when it is running on the same server as systemd unit.
   - `WorkingDirectory`: The installation directory of your bot.
   - `ExecStart`: The installation directory of the Python virtual environment.
5. Reload systemd: `sudo systemctl daemon-reload`
6. Enable the systemd unit: `sudo systemctl enable teamspeak-bot.service`
7. Start the systemd unit: `sudo systemctl start teamspeak-bot.service`

Further commands:

- Stop bot: `systemctl stop teamspeak-bot.service`
- Restart bot: `systemctl restart teamspeak-bot.service`

Next, checkout the [configuration](/docs/CONFIGURATION.md), if you haven't yet.
