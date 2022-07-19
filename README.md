# RetroSync (miniSNES Save Syncing)
Sync Retroarch saves between SNES classic and computer.

![alt-text](https://i.imgur.com/okP2PRD.png)
![alt-text](https://i.imgur.com/ENFLY63.png)

- Whenever a new battery save is generated (whether on computer directory or on snes classic) that new battery save is then converted and passed onto the other device.  Using this script is as simple running it on a computer, saving on either device, then seeing your battery save on the other device when starting up the game after about a minute or less.

- You may want to set the hotkey "Quit Retroarch" to DOWN+SELECT if you want saving to be handled properly when pressing the command to return to the SNES menu. Otherwise you will have to quit RetroArch manually.  This is not an issue with Canoe games. Unlike RetroArch games, moment a Canoe game is saved, the battery save is updated immediately.  After correctly quitting RetroArch, RetroArch battery saves will made the moment you return to the main menu after saving.

## Installation (App for macOS)
1.  You will need to have Hakchi CE installed on your SNES classic with wpa configured along with a OTG + WIFI dongle.
2.  Unzip the repository to `/Users/{user_name}/Documents/RetroSync`.
3.  Run the `python3 build.py` from within the designated directory. This will build `RetroSync.app` as well as install the essential Python packages.
4.  Move `RetroSync.app` to your applications folder.
5.  `/data/config.json` will be auto-generated if it does not exist upon boot. Modify accordingly (in GUI under `Configure...` or manually with text editor) then restart.


## Telegram Notifications Bot (optional)
![alt-text](https://i.imgur.com/jo4JVUA.jpg)
![alt-text](https://i.imgur.com/nwsJ1uW.jpg)

1.  On Telegram, add `BotFather` (https://t.me/BotFather) and create a new bot by requesting `/newbot`.
2.  Fill out the information, name the bot accordingly.  BotFather will present you with a token.  Add your token to `telegram_cofig.json` (via text editor or from the macOS App).
3.  Add `Telegram Bot Raw` (https://t.me/RawDataBot) and send it a message.  In its response, you will see something similar to tne following.
```
        "chat": {
            "id": 1234567890,
            ....
        },
```
4.  Now add your chat ID to `telegram_config.json` (via text editor or from the macOS App) and you should be good to go.

sidenote: Feel free to use the provided image for the telegram bot.


## RetroSync iOS/iCloud (recommended)
- You will need to set the RetroArch saves folder to `/{icloud_dir}/RetroArch/saves` in `config.json`.
- Under Automation within the Shortcuts app on your iPhone, add **RetroSync iCloud to iOS** to RetroArch as an automation script for opening the RetroArch iOS app and **RetroSync iOS to iCloud** as an automation script for closing the RetroArch iOS app.
- On the iPhone itself, new saves are pulled when the app is opened then pushed when the app is closed.

### RetroSync iOS to iCloud

https://www.icloud.com/shortcuts/7fbd2e2e02c74e9b9055fc2939e57a21

### RetroSync iCloud to iOS

https://www.icloud.com/shortcuts/5a9e26091cc34e7293cc2927f3242302

- (macOS Only) To prevent iCloud from constantly offloading a particular directory, in this case the RetroArch directory, locally on your Mac, you will want to install **Preserve iCloud Folders**, then set `USING_ICLOUD = True`.

### Preserve iCloud Folders (macOS Shortcuts script)

https://www.icloud.com/shortcuts/ad522b16a20a474c87f7a768fb278f7d

**sidenote:** If any of the folders on these Shortcuts are broken for some reason, just edit the Shortcut and point them to the correct directories.


## Installation (for just Python usage)
1.  You will need to have Hakchi CE installed on your SNES classic with wpa configured along with a OTG + WIFI dongle.
2.  Add the local IP for the SNES classic to `config.json` along with the retroarch folder on your computer you want to sync.
3.  To use the script enter `python3 /path/to/script/retro_sync.py` on the Command-Line.
4.  You can also use the `deploy.zsh` script to launch retro_sync in the background via Screen GNU.  To reattach to the process, type `screen -r retro_sync`.  To detatch, press `CTRL+A, CTRL+D`.

sidenote: Python script should be compatible with Windows and Linux.
