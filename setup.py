from distutils.core import setup
APP = ['app/retro_sync_app.py']
DATA_FILES = ['app/retro_sync_app.py', 'app/icon.icns', 'app/icon2.icns']
OPTIONS = {
    'argv_emulation': True,
    'iconfile': 'app/icon.icns',
    'plist': {
        'CFBundleShortVersionString': '0.2.0',
        'LSUIElement': True,
    },
    'packages': [],
}
setup(
    app=APP,
    name='RetroSync',
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
    install_requires=['rumps', 'ftpretty']
)