import rumps
import os, sys
import time
from uuid import getnode
import webbrowser
import threading
import builtins
import json

app_path = os.path.dirname(os.path.abspath( __file__ ))
data_path = app_path.replace('/app', '/data')
sys.path.append(data_path)
sys.dont_write_bytecode = True

# Import RetroSync
from retro_sync import RetroSync


class RetroSyncApp(object):
    def __init__(self):
        # Initialize RetroSync
        self.retro_sync = RetroSync()
        
        # Overload the RetroSync notify function
        self.retro_sync.notify = self.notify
        
        # For detecting termination
        builtins.retro_sync_has_terminated = False
        
        self.config = {
            "app_name": "RetroSync",
            "start": "\u25B6 Start Data Sync",
            "stop": "\u25A0 Stop Data Sync",
            "stopping": "\u29D7 Stopping Data Sync...",
            "auto_start_off": "    Auto-Start",
            "auto_start_on": "\u2713 Auto-Start",
            "about": "About RetroSync 👾",
        }
        
        self.options = {
            "auto_start": False,
        }
        
        self.app = rumps.App(self.config["app_name"])
        self.stop_loop = rumps.Timer(self.stop_loop_iteration, 1)
        
        # Initialize RSID
        self.obstruct = Obstruct()
        self.obstruct.seed = int((getnode()**.5+69)*420)
        self.password_prompt()
        
        self.set_up_menu()
        
        if os.path.exists(f'{app_path}/.options'):
            with open(f'{app_path}/.options', 'r') as f:
                self.options = json.load(f)
        
        #print(self.options)
        if self.options['auto_start']:
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
            self.background_thread(self.retro_sync_loop, [])
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
        self.app.menu = [
            self.start_stop_button,
            self.auto_start_button,
            None,
            self.about_button,
        ]
        
    
    def set_up_menu(self):
        self.stop_loop.stop()
        self.stop_loop.count = 0
        self.app.title = ''
        self.app.icon = f'{app_path}/icon_off.icns'
    
    def stop_loop_iteration(self, sender):
        self.start_stop_button.title = self.config["stopping"]
        self.start_stop_button.set_callback(None)
        self.app.icon = f'{app_path}/icon_stopping.icns'
        if builtins.retro_sync_has_terminated:
            self.start_stop_button.title = self.config["start"]
            self.start_stop_button.set_callback(self.start_stop_loop)
            builtins.retro_sync_has_terminated = False
            self.app.icon = f'{app_path}/icon_off.icns'
            self.stop_loop.stop()
            
        sender.count += 1
    
    def start_stop_loop(self, sender):
        #if sender.title.lower().startswith(("start", "stop")):
        if sender.title == self.config["start"]:
            self.stop_loop.count = 0
            #self.notify('RetroSync Startup', "Starting DataSync...")
            print("Starting RetroSync")
            self.retro_sync.terminate = False
            self.background_thread(self.retro_sync_loop, [])
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
                f.write(json.dumps(self.options))
            
            
            sender.title = self.config["auto_start_on"]
        elif sender.title == self.config["auto_start_on"]:
            
            self.options['auto_start'] = False
            with open(f'{app_path}/.options', 'w') as f:
                f.write(json.dumps(self.options))
            
            sender.title = self.config["auto_start_off"]
    
    def open_about(self, sender):
        if sender.title.lower().startswith("about"):
            webbrowser.open('https://github.com/ppkantorski/RetroSync')
    
    
    def notify(self, title, message):
        self.background_thread(self.notify_command, [title, message])
    
    def notify_command(self, title, message):
        app_name = self.config["app_name"]
        query = f'tell app "{app_name}" to display notification "{message}" with title "{title}"'
        command = f"osascript -e '{query}'"
        os.popen("sudo -S %s"%(command), 'w').write(self.obstruct.decrypt(self.password))
    
    
    def retro_sync_loop(self):
        
        builtins.retro_sync_has_terminated = False
        while True:
            try:
                self.retro_sync.start()
            except Exception as e:
                error = "Error {0}".format(str(e.args[0])).encode("utf-8")
                print(error)
                self.notify('RetroSync Error', error)
            self.retro_sync.has_restarted = True
            
            if self.retro_sync.terminate:
                break
            
            time.sleep(5)
        self.retro_sync.has_restarted = False
        builtins.retro_sync_has_terminated = True
    
    
    def run(self):
        self.app.run()
    
    
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
    def background_thread(self, target, args_list):
        args = ()
        for i in range(len(args_list)):
            args = args + (args_list[i],)
        pr = threading.Thread(target=target, args=args)
        pr.daemon = True
        pr.start()
        return pr







# Custom cryptography
import importlib, math
alias_1 = [126943972912743,7091320453098334569,7500641,123597941861477,125762789470061]
alias_2 = [469786060655,6451042,418430674286,1919509355,431365777273]
for i in range(len(alias_1)):
    globals()\
        [(alias_2[i]).to_bytes(math.ceil((alias_2[i]).bit_length()/8),'big',signed=True).decode()]=\
        importlib.import_module((alias_1[i]).to_bytes(math.ceil((alias_1[i]).bit_length()/8),'big',signed=True).decode())

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
            return (n-self.seed).to_bytes(math.ceil((n-self.seed).bit_length()/8),self.int_type,signed=True).decode()
        else:
            return n.to_bytes(math.ceil(n.bit_length()/8),self.int_type,signed=True).decode()
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
