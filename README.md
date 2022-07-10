# RetroSync
Sync Retroarch saves between SNES classic and computer

1.  You will need to have Hakchi CE installed on your SNES classic with wpa configured along with a OTG + WIFI dongle.
2.  Add the local IP for the SNES classic to the 'config.py' along with the retroarch folder on your computer you want to sync.
3.  You will need to install `ftpretty` via `pip3 install ftpretty`.
4.  To use enter `python3 /path/to/script/retro_sync.py`.  You can also use the `deploy.zsh` script to launch retro_sync in the background via Screen GNU.  To reattach to the process, type `screen -r retro_sync`.  To detatch, press `CTRL+A, CTRL+D`.
