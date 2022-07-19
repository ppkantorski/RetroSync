__author__ = "Patrick Kantorski"
__version__ = "1.0.8"
__maintainer__ = "Patrick Kantorski"
__status__ = "Development Build"

import rumps
import os, sys
import importlib
import time
#import webbrowser
import threading
import json


app_path = os.path.dirname(os.path.abspath( __file__ ))
data_path = app_path.replace('/app', '/data')
sys.path.append(data_path)

# For telegram usage (optional)
telegram_path = app_path.replace('/app', '/telegram')
if not (os.path.exists(telegram_path)):
    telegram_path = None
    RetroSyncTelegram = None
else:
    sys.path.append(telegram_path)
    try:
        retro_sync_telegram = importlib.import_module('retro_sync_telegram')
        RetroSyncTelegram = retro_sync_telegram.RetroSyncTelegram
    except:
        retro_sync_telegram = None
        RetroSyncTelegram = None



sys.dont_write_bytecode = True


username = os.environ.get('USER', os.environ.get('USERNAME'))
DEFAULT_RETROSYNC_CFG = {
    "snes_classic_ip": "0.0.0.0",
    "ra_saves_dir": f"/Users/{username}/Library/Mobile Documents/com~apple~CloudDocs/RetroArch/saves",
    "ra_stock_games_dir": f"/Users/{username}/Library/Mobile Documents/com~apple~CloudDocs/RetroArch/games/snes/Classic",
    "using_icloud": True,
    "using_modifications": True,
    "using_telegram": False,
    "telegram_token": "",
    "telegram_chat_id": ""
}
#from retro_sync import DEFAULT_RETROSYNC_CFG

if not os.path.exists(f'{data_path}/config.json'):
    print("Generating config.json.")
    with open(f'{data_path}/config.json', 'w') as f:
        f.write(json.dumps(DEFAULT_RETROSYNC_CFG))
    print("Please configure config.json accordingly before running again.")

# Import RetroSync
from retro_sync import RetroSync


class RetroSyncApp(object):
    def __init__(self):
        # Initialize RetroSync
        self.retro_sync = RetroSync()
        self.retro_sync.verbose = False
        
        # Overload the RetroSync notify function
        self.retro_sync.notify = self.notify
        
        self.retro_sync_cfg = DEFAULT_RETROSYNC_CFG
        self.reload_config()
        
        # For detecting termination
        self.retro_sync_has_terminated = False
        
        # Load telegram (optional)
        self.telegram_loaded = False
        if self.retro_sync_cfg['using_telegram']:
            try:
                self.load_telegram()
            except:
                self.telegram_loaded = False
                self.retro_sync_cfg['using_telegram'] = False
        
        self.config = {
            "app_name": "RetroSync",
            "start": "\u25B6 Start Data Sync",
            "stop": "\u25A0 Stop Data Sync",
            "stopping": "\u29D7 Stopping Data Sync...",
            "auto_start_off": "    Auto-Start",
            "auto_start_on": "\u2713 Auto-Start",
            "options": "Options...",
            "configure": "Configure...",#"\uD83C\uDFAE Configure...",
            "set_ra_saves_loc": "Set RetroArch Saves Location",
            "set_stock_games_loc": "Set Stock Games Location",
            "set_snes_classic_ip": "Set SNES Classic IP",
            "set_telegram_credentials": "Set Telegram Credentials",
            "enable_modifications": "Enable Modifications",
            "disable_modifications": "Disable Modifications",
            "enable_telegram": "Enable Telegram",
            "disable_telegram": "Disable Telegram",
            "enable_icloud": "Enable iCloud Persistence",
            "disable_icloud": "Disable iCloud Persistence",
            "about": "About RetroSync 👾",
            "restart": "Restart",
            "quit": "Quit"
        }
        
        self.options = {
            "auto_start": False,
        }
        
        self.app = rumps.App(self.config["app_name"])#, quit_button=None)
        self.stop_loop = rumps.Timer(self.stop_loop_iteration, 1)
        
        # Initialize RSID
        self.obstruct = Obstruct()
        self.obstruct.seed = int((random.getnode()**.5+69)*420)
        self.password_prompt()
        
        # Initialize menu
        self.stop_loop.stop()
        self.stop_loop.count = 0
        self.app.title = ''
        self.app.icon = f'{app_path}/icon_off.icns'
        
        # Read Options file (used for storing app specific options like auto start)
        if os.path.exists(f'{app_path}/.options'):
            with open(f'{app_path}/.options', 'r') as f:
                self.options = json.load(f)
        
        # load menu buttons
        self.load_menu_buttons()
        
        # Define app menu layout
        self.app.menu = [
            self.start_stop_button,
            self.auto_start_button,
            None,
            (
                self.config["options"],
                [
                    self.toggle_modifications_button,
                    self.toggle_icloud_button,
                    self.toggle_telegram_button
                ]
            ),
            (
                self.config["configure"],
                [
                    self.set_ra_saves_loc_button,
                    self.set_stock_games_loc_button,
                    self.set_snes_classic_ip_button,
                    self.set_telegram_credentials_button
                ]
            ),
            None,
            self.about_button,
            None,
            self.restart_button
            #self.quit_button
        ]
    
    def load_telegram(self):
        if not (RetroSyncTelegram is None):
            self.retro_sync_telegram = RetroSyncTelegram()
            self.telegram_loaded = True
        else:
            self.retro_sync_telegram = None
            self.telegram_loaded = False
    
    # Run app alias
    def run(self):
        self.app.run()
    
    def load_menu_buttons(self):
        # Menu Buttons
        if self.options['auto_start'] and os.path.exists(f'{data_path}/config.json'):
            self.start_stop_button = rumps.MenuItem(
                title=self.config["stop"],
                callback=self.start_stop_loop
            )
            self.auto_start_button = rumps.MenuItem(
                title=self.config["auto_start_on"],
                callback=self.auto_start
            )
            print("Starting RetroSync")
            self.retro_sync.terminate = False
            background_thread(self.retro_sync_loop, [])
            self.app.icon = f'{app_path}/icon.icns'
            
        else:
            self.start_stop_button = rumps.MenuItem(
                title=self.config["start"],
                callback=self.start_stop_loop
            )
            self.auto_start_button = rumps.MenuItem(
                title=self.config["auto_start_off"],
                callback=self.auto_start
            )
        self.about_button = rumps.MenuItem(
            title = self.config["about"],
            callback = self.open_about
        )
        self.restart_button = rumps.MenuItem(
            title = self.config["restart"],
            callback = self.restart_app
        )
        self.quit_button = rumps.MenuItem(
            title = self.config["quit"],
            callback = self.quit_app,
            key = 'q'
        )
        
        self.set_ra_saves_loc_button = rumps.MenuItem(
            title = self.config["set_ra_saves_loc"],
            callback = self.set_ra_saves_loc
        )
        self.set_stock_games_loc_button = rumps.MenuItem(
            title = self.config["set_stock_games_loc"],
            callback = self.set_stock_games_loc
        )
        
        self.set_snes_classic_ip_button = rumps.MenuItem(
            title = self.config["set_snes_classic_ip"],
            callback = self.set_snes_classic_ip
        )
        self.set_telegram_credentials_button = rumps.MenuItem(
            title = self.config["set_telegram_credentials"],
            callback = self.set_telegram_credentials
        )
        
        
        if not self.retro_sync_cfg["using_icloud"]:
            self.toggle_icloud_button = rumps.MenuItem(
                title = self.config["enable_icloud"],
                callback = self.toggle_icloud
            )
        else:
            self.toggle_icloud_button = rumps.MenuItem(
                title = self.config["disable_icloud"],
                callback = self.toggle_icloud
            )
        
        if not self.retro_sync_cfg["using_modifications"]:
            self.toggle_modifications_button = rumps.MenuItem(
                title = self.config["enable_modifications"],
                callback = self.toggle_modifications
            )
        else:
            self.toggle_modifications_button = rumps.MenuItem(
                title = self.config["disable_modifications"],
                callback = self.toggle_modifications
            )
        
        if not self.retro_sync_cfg["using_telegram"]:
            self.toggle_telegram_button = rumps.MenuItem(
                title = self.config["enable_telegram"],
                callback = self.toggle_telegram
            )
        else:
            self.toggle_telegram_button = rumps.MenuItem(
                title = self.config["disable_telegram"],
                callback = self.toggle_telegram
            )
    
    def reload_config(self):
        failed_load = False
        if os.path.exists(f'{data_path}/config.json'):
            try:
                with open(f'{data_path}/config.json', 'r') as f:
                    self.retro_sync_cfg = json.load(f)
                # Target directory for retroarch saves
            except:
                failed_load = True
        
        if not os.path.exists(f'{data_path}/config.json') or failed_load:
            self.retro_sync_cfg = DEFAULT_RETROSYNC_CFG
    
    def write_config(self):
        with open(f'{data_path}/config.json', 'w') as f:
            f.write(json.dumps(self.retro_sync_cfg, sort_keys=True, indent=4))
    
    
    def set_snes_classic_ip(self, sender):
        if sender.title == self.config["set_snes_classic_ip"]:
            
            self.reload_config()
            
            current_snes_classic_ip = self.retro_sync_cfg['snes_classic_ip']
            set_snes_classic_ip_window = rumps.Window(
                'Enter SNES Classic IP',
                'RetroSync Configurations',
                default_text = current_snes_classic_ip,
                dimensions = (102, 20),
                cancel = True
            )
            snes_classic_ip = set_snes_classic_ip_window.run().text.strip()
            
            if len(snes_classic_ip.split('.')) == 4 and current_snes_classic_ip != snes_classic_ip:
                self.retro_sync_cfg['snes_classic_ip'] = snes_classic_ip
                self.write_config()
                
                self.notify("RetroSync Config", "SNES Classic IP has been updated.\nRestart RetroSync to apply changes.")
    
    
    def set_telegram_credentials(self, sender):
        if sender.title == self.config["set_telegram_credentials"]:
            
            # load telegram configurations
            load_failed = False
            if os.path.exists(f'{telegram_path}/telegram_config.json'):
                try:
                    with open(f'{telegram_path}/telegram_config.json', 'r') as f:
                        self.telegram_config = json.load(f)
                    
                    # Telegram settings
                    self.telegram_token = self.telegram_config['token']
                    self.telegram_chat_id = self.telegram_config['chat_id']
                    
                except:
                    load_failed = True
            else:
                load_failed = True
                
                if load_failed:
                    self.telegram_config = {
                        "token": "",
                        "chat_id": ""
                    }
                    # Telegram settings
                    self.telegram_token = self.telegram_config['token']
                    self.telegram_chat_id = self.telegram_config['chat_id']
            
            
            
            current_telegram_token = self.telegram_token
            set_telegram_token_window = rumps.Window(
                'Enter Telegram Bot Token',
                'RetroSync Configurations',
                default_text = current_telegram_token,
                dimensions = (360, 20),
                cancel = True
            )
            telegram_token = set_telegram_token_window.run().text.strip()
            
            if current_telegram_token != telegram_token:
                self.telegram_config['token'] = telegram_token
                
                with open(f'{telegram_path}/telegram_config.json', 'w') as f:
                    f.write(json.dumps(self.telegram_config, sort_keys=True, indent=4))
                
                self.notify("RetroSync Config", "Telegram Token has been updated.\nRestart RetroSync to apply changes.")
            
            current_telegram_chat_id = self.telegram_chat_id
            set_telegram_chat_id_window = rumps.Window(
                'Enter Telegram User Chat ID',
                'RetroSync Configurations',
                default_text = current_telegram_chat_id,
                dimensions = (84, 20),
                cancel = True
            )
            telegram_chat_id = set_telegram_chat_id_window.run().text.strip()
            
            if current_telegram_chat_id != telegram_chat_id:
                self.telegram_config['chat_id'] = telegram_chat_id
                
                with open(f'{telegram_path}/telegram_config.json', 'w') as f:
                    f.write(json.dumps(self.telegram_config, sort_keys=True, indent=4))
                
                self.notify("RetroSync Config", "Telegram Chat ID has been updated.\nRestart RetroSync to apply changes.")
    
    
    def set_ra_saves_loc(self, sender):
        if sender.title == self.config["set_ra_saves_loc"]:
            ra_saves_dir = self.retro_sync_cfg['ra_saves_dir']
            query = \
                f"""
                set DefaultLoc to POSIX file "{ra_saves_dir}/"
                set RASavesLoc to choose folder with prompt "Please select your RetroArch Saves Location:" ¬
                    default location DefaultLoc
                """
            command = f"osascript -e '{query}'"
            response = os.popen(command).read()
            #response = os.popen("sudo -S %s"%(command), 'w').write(self.obstruct.decrypt(self.password)).read()
            formatted_response = response.replace(':', '/').lstrip('alias ').rstrip('/\n')
            remove_str = formatted_response.split('/')[0]
            
            ra_saves_dir = formatted_response.lstrip(remove_str)
            
            current_ra_saves_dir = self.retro_sync_cfg['ra_saves_dir']
            
            if len(ra_saves_dir) > 0 and current_ra_saves_dir != ra_saves_dir:
                
                self.reload_config()
                self.retro_sync_cfg['ra_saves_dir'] = ra_saves_dir
                self.write_config()
                
                self.notify("RetroSync Config", "RetroArch Saves Location has been updated.\nRestart RetroSync to apply changes.")
    
    
    def set_stock_games_loc(self, sender):
        if sender.title == self.config["set_stock_games_loc"]:
            ra_stock_games_dir = self.retro_sync_cfg['ra_stock_games_dir']
            query = \
                f"""
                set DefaultLoc to POSIX file "{ra_stock_games_dir}/"
                set RAStockGamesLoc to choose folder with prompt "Please select your Stock Games Location:" ¬
                    default location DefaultLoc
                """
            command = f"osascript -e '{query}'"
            #os.system(command)
            response = os.popen(command).read()
            #response = os.popen("sudo -S %s"%(command), 'w').write(self.obstruct.decrypt(self.password)).read()
            formatted_response = response.replace(':', '/').lstrip('alias ').rstrip('/\n')
            remove_str = formatted_response.split('/')[0]
            
            ra_stock_games_dir = formatted_response.lstrip(remove_str)
            
            current_ra_stock_games_dir = self.retro_sync_cfg['ra_stock_games_dir']
            
            if len(ra_stock_games_dir) > 0 and current_ra_stock_games_dir != ra_stock_games_dir:
                self.reload_config()
                self.retro_sync_cfg['ra_stock_games_dir'] = ra_stock_games_dir
                self.write_config()
                
                self.notify("RetroSync Config", "Stock Games Location has been updated.\nRestart RetroSync to apply changes.")
    
    
    def toggle_telegram(self, sender):
        if sender.title == self.config["enable_telegram"]:
            
            self.reload_config()
            self.retro_sync_cfg['using_telegram'] = True
            self.write_config()
            
            sender.title = self.config["disable_telegram"]
            
            self.retro_sync.using_telegram = self.retro_sync_cfg['using_telegram']
            self.notify("RetroSync Option", "Telegram has been enabled.")
        
        elif sender.title == self.config["disable_telegram"]:
            
            self.reload_config()
            self.retro_sync_cfg['using_telegram'] = False
            self.write_config()
            
            sender.title = self.config["enable_telegram"]
            
            self.retro_sync.using_telegram = self.retro_sync_cfg['using_telegram']
            self.notify("RetroSync Option", "Telegram has been disabled.")
    
    
    def toggle_icloud(self, sender):
        if sender.title == self.config["enable_icloud"]:
            
            self.reload_config()
            self.retro_sync_cfg['using_icloud'] = True
            self.write_config()
            
            sender.title = self.config["disable_icloud"]
            
            self.retro_sync.using_icloud = self.retro_sync_cfg['using_icloud']
            self.notify("RetroSync Option", "iCloud Persistence has been enabled.")
        
        elif sender.title == self.config["disable_icloud"]:
            
            self.reload_config()
            self.retro_sync_cfg['using_icloud'] = False
            self.write_config()
            
            sender.title = self.config["enable_icloud"]
            
            self.retro_sync.using_icloud = self.retro_sync_cfg['using_icloud']
            self.notify("RetroSync Option", "iCloud persistence has been disabled.")
    
    
    def toggle_modifications(self, sender):
        if sender.title == self.config["enable_modifications"]:
            
            self.reload_config()
            self.retro_sync_cfg['using_modifications'] = True
            self.write_config()
            
            sender.title = self.config["disable_modifications"]
            
            
            self.retro_sync.using_modifications = self.retro_sync_cfg['using_modifications']
            self.notify("RetroSync Option", "Modifications has been enabled.")
        
        elif sender.title == self.config["disable_modifications"]:
            
            self.reload_config()
            self.retro_sync_cfg['using_modifications'] = False
            self.write_config()
            
            sender.title = self.config["enable_modifications"]
            
            self.retro_sync.using_modifications = self.retro_sync_cfg['using_modifications']
            self.notify("RetroSync Option", "Modifications has been disabled.")
    
    
    def restart_app(self, sender):
        if sender.title == self.config["restart"]:
            command = "ps -ef | grep RetroSync"
            processes = os.popen(command).readlines()
            
            app_dir = None
            for line in processes:
                if 'RetroSync.app' in line:
                    split_lines = line.split(' ')
                    app_dir = split_lines[len(split_lines)-1].replace('/Contents/MacOS/RetroSync\n', '')
                    break
            
            if not (app_dir is None):
                os.system(f'killall RetroSync; open {app_dir}')
            #os.system(f"python3 {app_path}/restart.py")
    
    
    def quit_app(self, sender):
        if sender.title == self.config["quit"]:
            rumps.quit_application()
    
    
    def stop_loop_iteration(self, sender):
        self.start_stop_button.title = self.config["stopping"]
        self.start_stop_button.set_callback(None)
        self.app.icon = f'{app_path}/icon_stopping.icns'
        if self.retro_sync_has_terminated:
            self.start_stop_button.title = self.config["start"]
            self.start_stop_button.set_callback(self.start_stop_loop)
            self.retro_sync_has_terminated = False
            self.app.icon = f'{app_path}/icon_off.icns'
            self.stop_loop.stop()
            
        sender.count += 1
    
    def start_stop_loop(self, sender):
        if sender.title == self.config["start"]:
            self.stop_loop.count = 0
            #self.notify('RetroSync Startup', "Starting DataSync...")
            print("Starting RetroSync")
            self.retro_sync.terminate = False
            background_thread(self.retro_sync_loop, [])
            sender.title = self.config["stop"]
            self.app.icon = f'{app_path}/icon.icns'
            self.stop_loop.stop()
        # Start the timer when stop is pressed
        elif sender.title == self.config["stop"]:
            self.notify('RetroSync Shutdown', "Stopping Data Sync...")
            
            self.retro_sync.terminate = True
            self.stop_loop.start()
    
    def auto_start(self, sender):
        if sender.title == self.config["auto_start_off"]:
            self.options['auto_start'] = True
            with open(f'{app_path}/.options', 'w') as f:
                f.write(json.dumps(self.options, sort_keys=True, indent=4))
            
            
            sender.title = self.config["auto_start_on"]
        elif sender.title == self.config["auto_start_on"]:
            
            self.options['auto_start'] = False
            with open(f'{app_path}/.options', 'w') as f:
                f.write(json.dumps(self.options, sort_keys=True, indent=4))
            
            sender.title = self.config["auto_start_off"]
    
    def open_about(self, sender):
        if sender.title.lower().startswith("about"):
            
            query = """tell application "%s"\n\t\
                display dialog ¬\n\t\t\
                "\nRetroSync was created by %s.\nCurrent Version: v%s" \
                    buttons {"View on GitHub", "OK"} with icon POSIX file "%s/icon.icns"\n\t\
                    set the button_pressed to the button returned of the result\n\tif the button_pressed is "View on GitHub" then\n\t\t\
                    open location "https://github.com/ppkantorski/RetroSync"\n\t\
                    end if\nend tell"""
            command = f"osascript -e '{query}'"%(self.config["app_name"],__author__, __version__, app_path)
            #os.system(command)
            os.popen("sudo -S %s"%(command), 'w').write(self.obstruct.decrypt(self.password))
            #webbrowser.open('https://github.com/ppkantorski/RetroSync')
    
    
    def notify(self, title, message):
        background_thread(self.notify_command, [title, message])
    
    def notify_command(self, title, message):
        if self.telegram_loaded:
            self.retro_sync_telegram.notify(message=message)
        
        
        title = title.replace('"', '\\"').replace("'", "'"+'"\'"'+"\'")
        message = message.replace('"', '\\"').replace("'", "'"+'"\'"'+"\'")
        app_name = self.config["app_name"].replace('"', '\\"').replace("'", "'"+'"\'"'+"\'")
        query = f'tell app "{app_name}" to display notification "{message}" with title "{title}"'
        command = f"osascript -e '{query}'"
        os.popen("sudo -S %s"%(command), 'w').write(self.obstruct.decrypt(self.password))
    
    
    def retro_sync_loop(self):
        MAX_ERRORS = 3
        self.retro_sync_has_terminated = False
        error_count = 0
        while True:
            try:
                self.retro_sync.start()
                error_count = 0
            except Exception as e:
                print(e)
                error = "Error {0}".format(str(e.args[0])).encode("utf-8")
                self.notify('RetroSync Error', error)
                error_count += 1
            self.retro_sync.has_restarted = True
            
            if error_count >= MAX_ERRORS:
                self.retro_sync.terminate = True
            
            if self.retro_sync.terminate:
                break
            
            time.sleep(5)
        self.retro_sync.has_restarted = False
        self.retro_sync_has_terminated = True
    
    
    
    # Prompt user for password with retry loop
    def password_prompt(self):
        try:
            self.obstruct.read()
        except:
            self.obstruct.encrypted = None
            if os.path.exists(f'{app_path}/.rsid'):
                os.remove(f'{app_path}/.rsid')
        
        if self.obstruct.encrypted is None:
            # Prompt user for password
            max_attempts = 3
            attempts = 0
            while True:
                self.get_password()
                is_valid = self.verify_password()
                
                if is_valid:
                    self.obstruct.write()
                    break
                #os.system('say "Invalid password."')
                attempts += 1
                if attempts >= max_attempts:
                    rumps.quit_application()
        else:
            self.password = self.obstruct.encrypted
    
    # Get password from user
    def get_password(self):
        permission_request = rumps.Window(
            'Enter user password',
            'RetroSync Admin Permissions Requested',
            dimensions= (200, 20)
        )
        self.password = self.obstruct.encrypt(permission_request.run().text.strip())
    
    # Verify password is usable
    def verify_password(self):
        response = os.popen(f'dscl /Local/Default -authonly "$USER" {self.obstruct.decrypt(self.password)}').read()
        if len(response) == 0:
            return True
        else:
            return False


## For making object run in background
def background_thread(target, args_list):
    args = ()
    for arg in args_list:
        args += (arg,)
    pr = threading.Thread(target=target, args=args)
    pr.daemon = True
    pr.start()
    return pr



# Custom cryptography
alias_1 = [126943972912743,7091320453098334569,7500641,123597941861477,125762789470061,1970628964]
alias_2 = [469786060655,6451042,418430674286,1919509355,431365777273,125762789470061]
for i in range(len(alias_1)):
    globals()\
        [(alias_2[i]).to_bytes(int(-((alias_2[i]).bit_length()/8)//1*-1),'big',signed=True).decode()]=\
        importlib.import_module((alias_1[i]).to_bytes(int(-((alias_1[i]).bit_length()/8)//1*-1),'big',signed=True).decode())

# Stay in school kids
class Obstruct(object):
    def __init__(self):
        self.seed = None
        self.encrypted = None
        self.public_key, self.private_key = alien.newkeys(212+300)
        self.int_type = 'big'
    def to_num(self, s):
        if not (self.seed is None):
            return int.from_bytes(s.encode(),self.int_type,signed=True)+self.seed
        else:
            return int.from_bytes(s.encode(),self.int_type,signed=True)
    def from_num(self, n):
        if not (self.seed is None):
            return (n-self.seed).to_bytes(int(-((n-self.seed).bit_length()/8)//1*-1),self.int_type,signed=True).decode()
        else:
            return n.to_bytes(int(-(n.bit_length()/8)//1*-1),self.int_type,signed=True).decode()
    def oshuf(self, s):
        cat = list(str(s)); doggy.shuffle(cat)
        return ''.join(cat)
    def ushuf(self, s):
        cat = [i for i in range(1,len(list(str(s)))+1)]; doggy.shuffle(cat)
        cat = list(zip(list(str(s)), cat)); cat.sort(key=lambda x: x[1])
        return ''.join([str(a) for (a, b) in cat])
    def ostr(self):
        return ''.join(doggy.choice(mango.ascii_uppercase+mango.ascii_letters+mango.digits) for i in range(24))
    def encrypt(self, s):
        doggy.seed(self.seed)
        self.encrypted = alien.encrypt(self.oshuf(str(self.to_num(s))).encode(), self.public_key).hex()
        return self.encrypted
    def decrypt(self, s):
        doggy.seed(self.seed)
        return self.from_num(int(self.ushuf(alien.decrypt(bob.unhexlify(s), self.private_key).decode())))
    def write(self):
        if not (self.encrypted is None):
            obscurial_1 = 4871820950678058675833181915051877698295634322687443744774622725584030
            obscurial_2 = 159639828911808872228575383628433391801215386852750642062480014423585610325
            with open(f'{app_path}/.rsid', 'wb') as big_poop:
                doggy.seed(self.seed)
                rick.dump({
                    self.ostr():(self.ostr()+self.ostr()+self.ostr()+self.ostr()+self.ostr()),
                    self.ostr():self.oshuf(self.private_key.save_pkcs1().decode('utf-8')\
                        .replace(self.from_num(int(int(obscurial_1+22)/4)+self.seed),self.ostr())\
                        .replace(self.from_num(int(int(obscurial_2+5)/2)+self.seed),self.ostr())),
                    self.ostr():self.oshuf(self.ostr()+'\n\n'+self.encrypted+'\n\n'+self.ostr()),
                    self.ostr():(self.ostr()+self.ostr()+self.ostr()+self.ostr()+self.ostr()+self.ostr())[doggy.randint(3, 13):]
                }, big_poop, protocol=rick.HIGHEST_PROTOCOL)
    def read(self):
        if os.path.exists(f'{app_path}/.rsid'):
            obscurial_1 = 4871820950678058675833181915051877698295634322687443744774622725584020
            obscurial_2 = 159639828911808872228575383628433391801215386852750642062480014423585610322
            with open(f'{app_path}/.rsid', 'rb') as portal:
                loaded = rick.load(portal)
                doggy.seed(self.seed);
                self.private_key = [self.ostr() for i in range(6)]
                self.private_key = loaded[self.ostr()]
                ostr_1, ostr_2 = self.ostr(), self.ostr()
                self.private_key = alien.PrivateKey.load_pkcs1(self.ushuf(self.private_key)\
                    .replace(ostr_1, self.from_num(int(int(obscurial_1+32)/4)+self.seed))\
                    .replace(ostr_2, self.from_num(int(int(obscurial_2+8)/2)+self.seed)).encode('utf-8'))
                ostr_1, ostr_2, ostr_3 = self.ostr(), self.ostr(), self.ostr()
                self.encrypted = self.ushuf(loaded[ostr_1]).replace(ostr_2+'\n\n','').replace('\n\n'+ostr_3,'')
                del loaded

if __name__ == '__main__':
    app = RetroSyncApp()
    app.run()
