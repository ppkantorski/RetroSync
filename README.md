# RetroSync
Sync Retroarch saves between SNES classic and computer.

- Whenever a new battery save is generated (whether on computer directory or on snes classic) that new battery save is then passed onto the other device.  Using this script is as simple running it on a computer, saving on either device, then seeing your battery save on the other device when starting up the game after about a minute or less.

- You may want to set the hotkey "Quit Retroarch" to DOWN+SELECT if you want saving to be handled properly when pressing the command to return to the SNES menu. Otherwise you will have to quit RetroArch manually.  This is not an issue with Canoe games. Unlike RetroArch games, moment a Canoe game is saved, the battery save is updated immediately.  After changing the hotkeys, RetroArch battery saves will made the moment you return to the main menu after saving.


# Installation
1.  You will need to have Hakchi CE installed on your SNES classic with wpa configured along with a OTG + WIFI dongle.
2.  Add the local IP for the SNES classic to the `config.py` along with the retroarch folder on your computer you want to sync.
3.  You will need to install `ftpretty` via `pip3 install ftpretty`.
4.  To use the script enter `python3 /path/to/script/retro_sync.py` on the Command-Line.
5.  You can also use the `deploy.zsh` script to launch retro_sync in the background via Screen GNU.  To reattach to the process, type `screen -r retro_sync`.  To detatch, press `CTRL+A, CTRL+D`.
