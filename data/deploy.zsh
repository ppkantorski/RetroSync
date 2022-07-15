SCRIPTPATH=${0:A}
SCRIPTPATH="${SCRIPTPATH//deploy.zsh}"
screen -dmS retro_sync python3 "${SCRIPTPATH}retro_sync.py"
