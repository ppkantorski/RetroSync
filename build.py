import os
import shutil

# Install module if not already installed
import importlib
def install(package):
    try:
        importlib.import_module(package)
    except ImportError:
        os.system(f"pip3 install {package}")

# Import / Install
packages = ['ftpretty', 'py2app', 'rumps', 'python-telegram-bot']
[install(pkg) for pkg in packages]

# Define script path
script_path = os.path.dirname(os.path.abspath( __file__ ))

# Run setup script
os.system(f'python3 {script_path}/setup.py py2app -A')

# Clean up directories
shutil.rmtree(f'{script_path}/build')
os.system(f'mv {script_path}/dist/RetroSync.app {script_path}/RetroSync.app')
shutil.rmtree(f'{script_path}/dist')
