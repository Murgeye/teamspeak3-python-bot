# Update

This documentation describes, how you can update your bot to a newer version.

# Read release notes

First of all, you should read the release notes and understand them. You can find those here: https://github.com/Sebi94nbg/teamspeak3-python-bot/releases

There might be some breaking changes, which will affect your installation. Please check the release notes and do the necessary changes after the update, if required.

# Actual Update

1. Switch into the project directory: `cd teamspeak3-python-bot/`
2. Fetch the latest Git tags: `git fetch --tags`
3. Check on which version you are currently at: `git branch` (marked with a star in front of the line)
4. List available versions: `git tag`
5. Switch to the respective newer version: `git checkout <version>`
6. Confirm, that you are on the respective new version: `git branch` (marked with a star in front of the line)
7. If necessary, apply the necessary changes for the breaking changes from the release notes
8. Ensure, that you have the respective Git submodules installed: `git submodule update --init --recursive`
9. Ensure, that you have the respective Python requirements installed:
   - The systemd unit does this automatically. This is only needed, when you run the bot different.
   - Activate the Python virtual environment: `source venv/bin/activate`
   - Install the requirements: `pip3 install -r requirements.txt`
10. Restart the bot: `sudo systemctl restart teamspeak-bot.service` 

That's it. Your bot should be updated now and connected to your TeamSpeak server again.
