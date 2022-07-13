# RetroSync (miniSNES Save Syncing)
Sync Retroarch saves between SNES classic and computer.

- Whenever a new battery save is generated (whether on computer directory or on snes classic) that new battery save is then passed onto the other device.  Using this script is as simple running it on a computer, saving on either device, then seeing your battery save on the other device when starting up the game after about a minute or less.

- You may want to set the hotkey "Quit Retroarch" to DOWN+SELECT if you want saving to be handled properly when pressing the command to return to the SNES menu. Otherwise you will have to quit RetroArch manually.  This is not an issue with Canoe games. Unlike RetroArch games, moment a Canoe game is saved, the battery save is updated immediately.  After correctly quitting RetroArch, RetroArch battery saves will made the moment you return to the main menu after saving.


# Installation
1.  You will need to have Hakchi CE installed on your SNES classic with wpa configured along with a OTG + WIFI dongle.
2.  Add the local IP for the SNES classic to the `config.py` along with the retroarch folder on your computer you want to sync.
3.  To use the script enter `python3 /path/to/script/retro_sync.py` on the Command-Line.
4.  You can also use the `deploy.zsh` script to launch retro_sync in the background via Screen GNU.  To reattach to the process, type `screen -r retro_sync`.  To detatch, press `CTRL+A, CTRL+D`.

# RetroSync iOS/iCloud (optional)
- You will need to set the RetroArch saves folder to `/{icloud_dir}/RetroArch/saves` in the `config.py` file.
- Under Automation within the Shortcuts app on your iPhone, add **RetroSync iCloud to iOS** to RetroArch as an automation script for opening the RetroArch iOS app and **RetroSync iOS to iCloud** as an automation script for closing the RetroArch iOS app.
- On the iPhone itself, new saves are pulled when the app is opened then pushed when the app is closed.

RetroSync iOS to iCloud

https://www.icloud.com/shortcuts/7fbd2e2e02c74e9b9055fc2939e57a21

RetroSync iCloud to iOS

https://www.icloud.com/shortcuts/5a9e26091cc34e7293cc2927f3242302

- (macOS Only) To prevent iCloud from constantly offloading a particular directory, in this case the RetroArch directory, locally on your Mac, you will want to install **Preserve iCloud Folders**, then set `USING_ICLOUD = True`.

Preserve iCloud Folders (macOS Shortcuts script)

https://www.icloud.com/shortcuts/ad522b16a20a474c87f7a768fb278f7d

**sidenote:** If any of the folders on these Shortcuts are broken for some reason, just edit the Shortcut and point them to the correct directories.
