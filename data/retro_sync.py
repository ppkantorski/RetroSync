__author__ = "Patrick Kantorski"
__version__ = "1.0.6"
__maintainer__ = "Patrick Kantorski"
__status__ = "Development Build"

import binascii
import hashlib
import difflib
import filecmp
import json
import shutil 
import os, sys
import time
import datetime as dt
from pprint import pprint
import socket
from stat import S_ISDIR, S_ISREG
import threading

# Install module if not already installed
import importlib
def install_and_import(package):
    try:
        importlib.import_module(package)
    except ImportError:
        os.system(f"pip3 install {package} --quiet")
    finally:
        globals()[package] = importlib.import_module(package)

# Import / Install ftpretty
install_and_import('ftpretty')

# Define script path
script_path = os.path.dirname(os.path.abspath( __file__ ))
sys.path.append(script_path)
sys.dont_write_bytecode = True


#import config as cfg

# alias for now function
now = dt.datetime.now

RETRO_SYNC_DIR = script_path
LOCAL_CLASSIC_SAVES_TMP_DIR = f'{RETRO_SYNC_DIR}/save_data/snes_mini/.tmp/saves'
LOCAL_CLASSIC_SAVES_DIR = f'{RETRO_SYNC_DIR}/save_data/snes_mini/saves'
LOCAL_CLASSIC_META_DIR = f'{RETRO_SYNC_DIR}/save_data/snes_mini/meta'
LOCAL_RA_SAVES_TMP_DIR = f'{RETRO_SYNC_DIR}/save_data/retroarch/.tmp/saves'
LOCAL_RA_SAVES_DIR = f'{RETRO_SYNC_DIR}/save_data/retroarch/saves'

# Define SNES Classic Saves / Games directory (on device itself)
CLASSIC_SAVES_DIR = '/var/lib/clover/profiles/0'
CLASSIC_GAMES_DIR = '/var/lib/hakchi/games/snes-usa/.storage'
#CLASSIC_SAVES_DIR = f'{RETRO_SYNC_DIR}/test_data/saves'
#CLASSIC_GAMES_DIR = f'{RETRO_SYNC_DIR}/test_data/storage'

username = os.environ.get('USER', os.environ.get('USERNAME'))
DEFAULT_RETROSYNC_CFG = {
    "snes_classic_ip": "0.0.0.0",
    "ra_saves_dir": f"/Users/{username}/Library/Mobile Documents/com~apple~CloudDocs/RetroArch/saves",
    "ra_stock_games_dir": f"/Users/{username}/Library/Mobile Documents/com~apple~CloudDocs/RetroArch/games/snes/Classic",
    "using_icloud": True,
    "using_modifications": True
}


load_failed = False
if os.path.exists(f'{script_path}/config.json'):
    try:
        with open(f'{script_path}/config.json', 'r') as f:
            cfg = json.load(f)
        # Target directory for retroarch saves
        SNES_CLASSIC_IP = cfg['snes_classic_ip']
        RA_SAVES_DIR = cfg['ra_saves_dir']
        RA_STOCK_GAMES_DIR = cfg['ra_stock_games_dir']
        USING_ICLOUD = cfg['using_icloud']
        USING_MODIFICATIONS = cfg['using_modifications']
        
        if len(SNES_CLASSIC_IP) == 0 or len(RA_SAVES_DIR) == 0 or len(RA_STOCK_GAMES_DIR) == 0:
            load_failed = True
    except:
        load_failed = True
    
if not (os.path.exists(f'{script_path}/config.json')) or load_failed:
    cfg = DEFAULT_RETROSYNC_CFG
    print("Generating config.json.")
    with open(f'{script_path}/config.json', 'w') as f:
        f.write(json.dumps(cfg, sort_keys=True, indent=4))
    print("Please configure config.json accordingly before running again.")


TIMEOUT = 3 # check every X seconds
ICLOUD_TIMEOUT = 4 # Preserve iCloud folders every X hours


STOCK_GAME_ID_DICT = {
    "CLV-P-SACCE": "CONTRA III THE ALIEN WARS",
    "CLV-P-SAALE": "Donkey Kong Country",
    "CLV-P-SAAJE": "EarthBound",
    "CLV-P-SABTE": "Final Fantasy III",
    "CLV-P-SAABE": "F-ZERO",
    "CLV-P-SAAQE": "Kirby Super Star",
    "CLV-P-SAAKE": "Kirby's Dream Course",
    "CLV-P-SABCE": "Mega Man X",
    "CLV-P-SABRE": "Secret of Mana",
    "CLV-P-SADGE": "Star Fox",
    "CLV-P-SADKE": "Star Fox 2",
    "CLV-P-SABHE": "Street Fighter II Turbo: Hyper Fighting",
    "CLV-P-SACBE": "Super Castlevania IV",
    "CLV-P-SABDE": "Super Ghouls'n Ghosts",
    "CLV-P-SAAFE": "Super Mario Kart",
    "CLV-P-SABQE": "Super Mario RPG: Legend of the Seven Stars",
    "CLV-P-SAAAE": "Super Mario World",
    "CLV-P-SAAHE": "Super Metroid",
    "CLV-P-SAAXE": "Super Punch-Out!!",
    "CLV-P-SAAEE": "The Legend of Zelda: A Link to the Past",
    "CLV-P-SADJE": "Yoshi's Island"
}

STOCK_GAME_HEX_OFFSET = {
    "CLV-P-SAAQE": ('1F00', '1FFE'), #Kirby Super Star
    "CLV-P-SADKE": ('3912', '3A45'), #Star Fox 2
    "CLV-P-SABQE": ('0', '1FFC'), #Super Mario RPG: Legend of the Seven Stars
    "CLV-P-SADJE": ('7C00', '7E7B'), #Yoshi's Island
}



# Add custom download function to 'ftpretty'
class ftpretty_mod(ftpretty.ftpretty):
    def __init__(self, *args):
        ftpretty.ftpretty.__init__(self, *args)
        self.extensions = ['.sram',  '.hash']
        self.exclusions = ['CLV-G', 'CLV-Z', 'suspendpoint']
        self.buffer = 0.01
    def get_tree_custom(self, remote, local):
        """ Recursively download a directory tree with extensions filter.
        """
        #time.sleep(self.buffer) # Buffer to prevent rapid calls
        
        remote = remote.replace('\\', '/')
        entries = self.list(remote, extra=True)
        for entry in entries:
            name = entry['name']
            remote_path = os.path.join(remote, name)
            local_path = os.path.join(local, name)
            if entry.flags == 'd':
                
                continue_search = True
                for exclusion in self.exclusions:
                    if exclusion in remote_path:
                        continue_search = False
                        break
                
                if continue_search and 'CLV-' in remote_path:
                    if not os.path.exists(local_path):
                        os.mkdir(local_path)
                    self.get_tree_custom(remote_path, local_path)
            elif entry.flags == '-':
                for extension in self.extensions:
                    if extension in remote_path:
                        #time.sleep(self.buffer) # Buffer to prevent rapid calls
                        self.get(remote_path, local_path)
                        break
            else:
                pass

class RetroSync(object):
    def __init__(self):
        # Server Presets
        self.user_name = 'root'
        self.password = ''
        self.snes_classic_ip = SNES_CLASSIC_IP
        self.snes_classic_port = 22
        
        # Initialize
        self.terminate = False
        self.has_restarted = False
        #elf.ftp = None
        self.ftp = None
        #self.transport = None
        self.game_id_list = []
        self.game_id_dict = {}
        self.canoe_game_id_list = []
        self.canoe_game_id_dict = {}
        self.snes_update_list = []
        self.ra_update_list = []
        
        self.stock_game_id_dict = STOCK_GAME_ID_DICT
        self.stock_game_id_list = list(self.stock_game_id_dict.keys())
        
        # Safety Presets
        self.using_modifications = USING_MODIFICATIONS
        self.using_icloud = USING_ICLOUD
       
        # Default Print Presets
        self.verbose = False
        
        # Initialize Directories
        self.ra_saves_is_empty = False
        self.initialize_directories()
    
    def initialize_directories(self):
        local_directories = [
            LOCAL_CLASSIC_SAVES_TMP_DIR,
            LOCAL_CLASSIC_SAVES_DIR,
            LOCAL_CLASSIC_META_DIR,
            LOCAL_RA_SAVES_TMP_DIR,
            LOCAL_RA_SAVES_DIR
        ]
        for directory in local_directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
        
        if not os.path.exists(RA_SAVES_DIR):
            os.makedirs(RA_SAVES_DIR)
        
        dir_list = [i for i in os.listdir(RA_SAVES_DIR) if i != '.DS_Store']
        self.ra_saves_is_empty = (len(dir_list) == 0)
        
        if self.ra_saves_is_empty:
            if self.verbose:
                print(f'[{now()}] RetroArch Saves directory is empty.')
                print(f'[{now()}] Saves will be populated from SNES.')
    
    # For making object run in background
    def background_thread(self, target, args_list):
        args = ()
        for arg in args_list:
            args += (arg,)
        pr = threading.Thread(target=target, args=args)
        pr.daemon = True
        pr.start()
        return pr
    
    def notify(self, title, message):
        # Notifications are currenly only working on macOS
        if sys.platform == 'darwin':
            self.background_thread(self.notify_command, [title, message])
    
    def notify_command(self, title, message):
        os.system(
            """
            osascript -e 'display notification "{}" with title "{}"'
            """.format(message.replace('"', '\\"').replace("'", "'"+'"\'"'+"\'"), \
                title.replace('"', '\\"').replace("'", "'"+'"\'"'+"\'"))
        )
        
        #app_name = "RetroSync"
        #query = f'tell app "{app_name}" to display notification "{message}" with title "{title}"'
        #command = f"osascript -e '{query}'"
        ##print(self.decrypt(self.password))
        ##print(password)
        #os.popen("sudo -S %s"%(command), 'w').write(self.obstruct.decrypt(self.password))
        
    
    def check_connection(self):
        if self.snes_classic_ip == DEFAULT_RETROSYNC_CFG['snes_classic_ip']:
            return False
        try:
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.connect((self.snes_classic_ip, self.snes_classic_port))
        except:
            # not up, log reason from ex if wanted
            return False
        else:
            test_socket.close()
        return True
    
    
    def connect_to_ftp(self):
        self.ftp = ftpretty_mod(self.snes_classic_ip, self.user_name, self.password)
    
    def disconnect_from_ftp(self):
        if not (self.ftp is None):
            self.ftp.close()
    
    def upload_file_via_ftp(self, from_path, to_path):
        self.connect_to_ftp()
        self.ftp.put(from_path, to_path)
        self.disconnect_from_ftp()
    
    def download_file_via_ftp(self, from_path, to_path):
        self.connect_to_ftp()
        try:
            self.ftp.get(from_path, to_path)
        except:
            pass
        self.disconnect_from_ftp()
    
    def download_dir_via_ftp(self, from_path, to_path):
        self.connect_to_ftp()
        self.ftp.get_tree_custom(from_path, to_path)
        self.disconnect_from_ftp()
    
    def copy_and_overwrite(self, from_path, to_path):
        if os.path.exists(to_path):
            shutil.rmtree(to_path)
        shutil.copytree(from_path, to_path)
    
    def pull_saves(self, target):
        if target == 'snes':
            # Download saves on SNES Classic to temp directory
            #if os.path.exists(LOCAL_CLASSIC_SAVES_TMP_DIR):
            #    shutil.rmtree(LOCAL_CLASSIC_SAVES_TMP_DIR)
            if not os.path.exists(LOCAL_CLASSIC_SAVES_TMP_DIR):
                os.mkdir(LOCAL_CLASSIC_SAVES_TMP_DIR)
            self.download_dir_via_ftp(CLASSIC_SAVES_DIR, LOCAL_CLASSIC_SAVES_TMP_DIR)
        elif target == 'retroarch':
            # Copy saves from Retroarch to temp directory
            self.copy_and_overwrite(RA_SAVES_DIR, LOCAL_RA_SAVES_TMP_DIR)
    
    def update_local_saves(self, target, save_type='retroarch'):
        if target == 'snes':
            if save_type == 'canoe':
                for game_id in self.canoe_game_id_dict.keys():
                    save_data = f'{LOCAL_CLASSIC_SAVES_DIR}/{game_id}/cartridge.sram'
                    tmp_save_data = f'{LOCAL_CLASSIC_SAVES_TMP_DIR}/{game_id}/cartridge.sram'
                    
                    hash_data = f'{LOCAL_CLASSIC_SAVES_DIR}/{game_id}/cartridge.sram.hash'
                    tmp_hash_data = f'{LOCAL_CLASSIC_SAVES_TMP_DIR}/{game_id}/cartridge.sram.hash'
                    
                    # make the save container if it does not exist
                    save_container = save_data.replace('/cartridge.sram', '')
                    tmp_save_container = tmp_save_data.replace('/cartridge.sram', '')
                    
                    if os.path.exists(tmp_save_data):
                        if not os.path.exists(save_container):
                            os.mkdir(save_container)
                            shutil.copyfile(tmp_save_data, save_data)
                            shutil.copyfile(tmp_hash_data, hash_data)
                            #self.copy_and_overwrite(tmp_save_container, save_container)
                        # if save data exists and new save data is different
                        if os.path.exists(save_data):
                            is_same_data = filecmp.cmp(tmp_save_data, save_data)
                            if not is_same_data:
                                if self.verbose:
                                    print(f'{tmp_save_data} is not the same as {save_data}')
                                shutil.copyfile(tmp_save_data, save_data)
                                shutil.copyfile(tmp_hash_data, hash_data)
                                self.snes_update_list.append(game_id)
                                self.snes_update_list = list(set(self.snes_update_list))
                        else:
                            shutil.copyfile(tmp_save_data, save_data)
            elif save_type == 'retroarch':
                
                for game_id in self.game_id_dict.keys():
                    save_data = f'{LOCAL_CLASSIC_SAVES_DIR}/{game_id}/cartridge.sram'
                    tmp_save_data = f'{LOCAL_CLASSIC_SAVES_TMP_DIR}/{game_id}/cartridge.sram'
                    
                    # make the save container if it does not exist
                    save_container = save_data.replace('/cartridge.sram', '')
                    tmp_save_container = tmp_save_data.replace('/cartridge.sram', '')
                    
                    if os.path.exists(tmp_save_data):
                        if not os.path.exists(save_container):
                            os.mkdir(save_container)
                            shutil.copyfile(tmp_save_data, save_data)
                            #self.copy_and_overwrite(tmp_save_container, save_container)
                        # if save data exists and new save data is different
                        if os.path.exists(save_data):
                            is_same_data = filecmp.cmp(tmp_save_data, save_data)
                            if not is_same_data:
                                if self.verbose:
                                    print(f'{tmp_save_data} is not the same as {save_data}')
                                shutil.copyfile(tmp_save_data, save_data)
                                self.snes_update_list.append(game_id)
                                self.snes_update_list = list(set(self.snes_update_list))
                        else:
                            shutil.copyfile(tmp_save_data, save_data)
        
        elif target == 'retroarch':
            if save_type == 'canoe':
                for game_id in self.canoe_game_id_dict.keys():
                    file_name = self.canoe_game_id_dict[game_id]
                    save_data = f'{LOCAL_RA_SAVES_DIR}/{file_name}.srm'
                    tmp_save_data = f'{LOCAL_RA_SAVES_TMP_DIR}/{file_name}.srm'
                    
                    if os.path.exists(tmp_save_data):
                        # if save data exists and new save data is different
                        if os.path.exists(save_data):
                            is_same_data = filecmp.cmp(tmp_save_data, save_data)
                            if not is_same_data:
                                if self.verbose:
                                    print(f'{tmp_save_data} is not the same as {save_data}')
                                shutil.copyfile(tmp_save_data, save_data)
                                self.ra_update_list.append(game_id)
                                self.ra_update_list = list(set(self.ra_update_list))
                        else:
                            shutil.copyfile(tmp_save_data, save_data)
            elif save_type == 'retroarch':
                for game_id in self.game_id_dict.keys():
                    file_name = self.game_id_dict[game_id]
                    save_data = f'{LOCAL_RA_SAVES_DIR}/{file_name}.srm'
                    tmp_save_data = f'{LOCAL_RA_SAVES_TMP_DIR}/{file_name}.srm'
                    
                    if os.path.exists(tmp_save_data):
                        # if save data exists and new save data is different
                        if os.path.exists(save_data):
                            is_same_data = filecmp.cmp(tmp_save_data, save_data)
                            if not is_same_data:
                                if self.verbose:
                                    print(f'{tmp_save_data} is not the same as {save_data}')
                                shutil.copyfile(tmp_save_data, save_data)
                                self.ra_update_list.append(game_id)
                                self.ra_update_list = list(set(self.ra_update_list))
                        else:
                            shutil.copyfile(tmp_save_data, save_data)
    
    def generate_game_id_dicts(self):
        # Generate list of game IDs from classic tmp dir
        directory_list = os.listdir(LOCAL_CLASSIC_SAVES_TMP_DIR)
        self.game_id_list = [k for k in directory_list if 'CLV' in k and 'CLV-U' not in k and 'CLV-P' not in k]
        self.canoe_game_id_list = [k for k in directory_list if 'CLV-U' in k or 'CLV-P' in k]
        
        self.game_id_dict = {}
        for game_id in self.game_id_list:
            remote_file = f'{CLASSIC_GAMES_DIR}/{game_id}/metadata.json'
            local_file = f'{LOCAL_CLASSIC_META_DIR}/{game_id}.json'
            
            if not os.path.exists(local_file):
                self.download_file_via_ftp(remote_file, local_file)
            try:
                # Read game name from meta data
                with open(local_file) as json_file:
                    meta_data = json.load(json_file)
                self.game_id_dict[game_id] = meta_data['OriginalFilename'].rsplit(".", 1)[0]
            except:
                pass
        
        self.game_id_list = list(self.game_id_dict.keys())
        
        
        self.canoe_game_id_dict = {}
        for game_id in self.canoe_game_id_list:
            remote_file = f'{CLASSIC_GAMES_DIR}/{game_id}/metadata.json'
            local_file = f'{LOCAL_CLASSIC_META_DIR}/{game_id}.json'
            
            if not os.path.exists(local_file):
                self.download_file_via_ftp(remote_file, local_file)
            try:
                # Read game name from meta data
                with open(local_file) as json_file:
                    meta_data = json.load(json_file)
                self.canoe_game_id_dict[game_id] = meta_data['OriginalFilename'].rsplit(".", 1)[0]
            except:
                pass
        
        
        # Generate Game ID Dict with correct name association and attach i
        self.generate_stock_game_id_dict()
        
        self.canoe_game_id_list = list(self.canoe_game_id_dict.keys())
        
        if self.ra_saves_is_empty:
            self.snes_update_list = self.game_id_list + self.canoe_game_id_list
            self.ra_saves_is_empty = False
    
    
    def generate_stock_game_id_dict(self):
        game_ids = list(STOCK_GAME_ID_DICT.keys())
        actual_game_names = list(STOCK_GAME_ID_DICT.values())
        game_names = [x.lower() for x in actual_game_names]
        actual_file_names = [os.path.splitext(x)[0] for x in os.listdir(RA_STOCK_GAMES_DIR) if not x.startswith('.')]
        file_names = [self.remove_prefix(x.lower()) for x in actual_file_names]
        
        
        for i in range(len(game_names)):
            game_name = game_names[i]
            #pprint(file_names)
            #print('game_name:', game_name)
            closest_match = difflib.get_close_matches(game_name, file_names, n=1, cutoff=0.5)
            #print(closest_match)
            if len(closest_match) > 0:
                closest_match = closest_match[0]
                index = file_names.index(closest_match)
                self.canoe_game_id_dict[game_ids[i]] = actual_file_names[index]
            else:
                if self.verbose:
                    print(f'{actual_game_names[i]} could not be found. {closest_match}')
        #pprint(self.canoe_game_id_dict)
    
    def remove_prefix(self, string):
        while True:
            start_index = string.find('(')
            end_index = string.find(')')
            if start_index != -1 and end_index != -1:
                string = string[0:start_index]+string[end_index+1:]
            elif start_index == -1 or end_index == -1:
                break
        while True:
            start_index = string.find('[')
            end_index = string.find(']')
            if start_index != -1 and end_index != -1:
                string = string[0:start_index]+string[end_index+1:]
            elif start_index == -1 or end_index == -1:
                break
        string = string.rstrip(' ')
        return string
    
    def hex_to_index(self, hex_offset):
        return int(hex_offset, 16)*2
    
    def convert_save_to_canoe(self, from_file, to_dir, game_id):
        
        if game_id in STOCK_GAME_HEX_OFFSET.keys():
            use_hex_offset = True
        else:
            use_hex_offset = False
        
        with open(from_file, 'rb') as sramfile:
            sram_data = sramfile.read()
        
        if use_hex_offset:
            print(f'[{now()}] Using HEX offset for specified game {game_id}.')
            start_hex, end_hex = STOCK_GAME_HEX_OFFSET[game_id]
            start_index, end_index = int(self.hex_to_index(start_hex)), int(self.hex_to_index(end_hex))+2
            sram_data_hex = sram_data.hex()
            #print(sram_data_hex[start_index:end_index])
            sram_hash = hashlib.sha1(binascii.unhexlify(sram_data_hex[start_index:end_index]))
        else:
            sram_hash = hashlib.sha1(sram_data)
        
        with open(f'{to_dir}/cartridge.sram','wb') as output_sram:
            output_sram.write(sram_data)
            output_sram.write(sram_hash.digest())
        with open(f'{to_dir}/cartridge.sram.hash','wb') as output_hash:
            output_hash.write(sram_hash.digest())
        
        if self.verbose:
            print(f'[{now()}] Cartridge.sram and cartridge.sram.hash are now ready.')
    
    def convert_save_to_retroarch(self, from_file, to_file):
        if os.path.exists(from_file):
            with open(from_file, 'rb') as sramfile:
                sram_data = sramfile.read()
            
            with open(to_file, 'wb') as output_srm:
                output_srm.write(sram_data)
    
    
    # save_type: 'canoe' or 'retroarch'
    # target: 'retroarch' or 'snes'
    def convert_save(self, game_id, target, save_type='retroarch'):
        if save_type == 'retroarch':
            file_name = self.game_id_dict[game_id]
            if target == 'retroarch':
                shutil.copyfile(f'{LOCAL_CLASSIC_SAVES_DIR}/{game_id}/cartridge.sram', f'{LOCAL_RA_SAVES_DIR}/{file_name}.srm') # copy and convert
                if self.verbose:
                    print(f'[{now()}] Retroarch save for {file_name} has been overwritten by classic save.')
                self.notify(title='RetroSync Overwrite', message=f'Retroarch save for {file_name} has been overwritten by Classic save.')
            elif target == 'snes':
                shutil.copyfile(f'{LOCAL_RA_SAVES_DIR}/{file_name}.srm', f'{LOCAL_CLASSIC_SAVES_DIR}/{game_id}/cartridge.sram')
                self.notify(title='RetroSync Overwrite', message=f'Classic save for {file_name} has been overwritten by Retroarch save.')
                if self.verbose:
                    print(f'[{now()}] Classic save for {file_name} has been overwritten by retroarch save.')
        elif save_type == 'canoe':
            file_name = self.canoe_game_id_dict[game_id]
            if target == 'retroarch':
                #shutil.copyfile(f'{LOCAL_CLASSIC_SAVES_DIR}/{game_id}/cartridge.sram', f'{LOCAL_RA_SAVES_DIR}/{file_name}.srm') # copy and convert
                from_file = f'{LOCAL_CLASSIC_SAVES_DIR}/{game_id}/cartridge.sram'
                to_file = f'{LOCAL_RA_SAVES_DIR}/{file_name}.srm'
                self.convert_save_to_retroarch(from_file, to_file)
                self.notify(title='RetroSync Overwrite', message=f'Retroarch save for {file_name} has been overwritten by Classic save.')
                if self.verbose:
                    print(f'[{now()}] Retroarch save for {file_name} has been overwritten by classic save.')
            elif target == 'snes':
                from_file = f'{LOCAL_RA_SAVES_DIR}/{file_name}.srm'
                to_dir = f'{LOCAL_CLASSIC_SAVES_DIR}/{game_id}'
                self.convert_save_to_canoe(from_file, to_dir, game_id)
                #shutil.copyfile(from_file, to_file)
                self.notify(title='RetroSync Overwrite', message=f'Classic save for {file_name} has been overwritten by Retroarch save.')
                if self.verbose:
                    print(f'[{now()}] Classic save for {file_name} has been overwritten by retroarch save.')
    
    # save_type: 'canoe' or 'retroarch'
    # target: 'retroarch' or 'snes'
    def convert_saves(self, target, save_type='retroarch'):
        if save_type == 'retroarch':
            if target == 'retroarch':
                # Copy saves to local directory (backup too)
                for game_id in self.game_id_dict.keys():
                    file_name = self.game_id_dict[game_id]
                    shutil.copyfile(f'{LOCAL_CLASSIC_SAVES_DIR}/{game_id}/cartridge.sram', f'{LOCAL_RA_SAVES_TMP_DIR}/{file_name}.srm') # copy and convert
                    shutil.copyfile(f'{LOCAL_CLASSIC_SAVES_DIR}/{game_id}/cartridge.sram', f'{LOCAL_RA_SAVES_DIR}/{file_name}.srm') # copy and convert
                    if self.verbose:
                        print(f'[{now()}] Retroarch save for {file_name} has been overwritten by Classic save.')
            elif target == 'snes':
                # Copy saves to local directory (backup too)
                for game_id in self.game_id_dict.keys():
                    file_name = self.game_id_dict[game_id]
                    shutil.copyfile(f'{LOCAL_RA_SAVES_DIR}/{file_name}.srm', f'{LOCAL_CLASSIC_SAVES_TMP_DIR}/{game_id}/cartridge.sram')
                    shutil.copyfile(f'{LOCAL_RA_SAVES_DIR}/{file_name}.srm', f'{LOCAL_CLASSIC_SAVES_DIR}/{game_id}/cartridge.sram')
                    if self.verbose:
                        print(f'[{now()}] Classic save for {file_name} has been overwritten by Retroarch save.')
        elif save_type == 'canoe':
            if target == 'retroarch':
                # Copy saves to local directory (backup too)
                for game_id in self.canoe_game_id_dict.keys():
                    file_name = self.canoe_game_id_dict[game_id]
                    from_file = f'{LOCAL_CLASSIC_SAVES_DIR}/{game_id}/cartridge.sram'
                    self.convert_save_to_retroarch(from_file, f'{LOCAL_RA_SAVES_TMP_DIR}/{file_name}.srm')
                    self.convert_save_to_retroarch(from_file, f'{LOCAL_RA_SAVES_DIR}/{file_name}.srm')
                    
                    if self.verbose:
                        print(f'[{now()}] Retroarch save for {file_name} has been overwritten by Classic save.')
            elif target == 'snes':
                # Copy saves to local directory (backup too)
                for game_id in self.canoe_game_id_dict.keys():
                    file_name = self.canoe_game_id_dict[game_id]
                    from_file = f'{LOCAL_RA_SAVES_DIR}/{file_name}.srm'
                    self.convert_save_to_canoe(from_file, f'{LOCAL_CLASSIC_SAVES_DIR}/{game_id}')
                    self.convert_save_to_canoe(from_file, f'{LOCAL_CLASSIC_SAVES_TMP_DIR}/{game_id}')
                    
                    if self.verbose:
                        print(f'[{now()}] Classic save for {file_name} has been overwritten by Retroarch save.')
    
    def push_save(self, game_id, target, save_type='retroarch'):
        if save_type == 'retroarch':
            if target == 'snes':
                local_file_path = f'{LOCAL_CLASSIC_SAVES_DIR}/{game_id}/cartridge.sram'
                remote_file_path = f'{CLASSIC_SAVES_DIR}/{game_id}/cartridge.sram'
                if os.path.exists(local_file_path):
                    self.upload_file_via_ftp(local_file_path, remote_file_path)
                    if self.verbose:
                        print(f'[{now()}] {local_file_path} has been uploaded to {remote_file_path}.')
                #os.system(f"ftp {self.user_name}@{self.host}:{remote_path} <<< $'put {local_file_path}'")
            elif target == 'retroarch':
                file_name = self.game_id_dict[game_id]
                local_file_path = f'{LOCAL_RA_SAVES_DIR}/{file_name}.srm'
                remote_file_path = f'{RA_SAVES_DIR}/{file_name}.srm'
                # now push to retroarch directory
                if os.path.exists(local_file_path):
                    shutil.copyfile(local_file_path, remote_file_path)
                    if self.verbose:
                        print(f'[{now()}] {local_file_path} has been copied to {remote_file_path}.')
                #os.system()RA_SAVES_DIR
        elif save_type == 'canoe':
            if target == 'snes':
                local_file_path = f'{LOCAL_CLASSIC_SAVES_DIR}/{game_id}/cartridge.sram'
                remote_file_path = f'{CLASSIC_SAVES_DIR}/{game_id}/cartridge.sram'
                if os.path.exists(local_file_path):
                    self.upload_file_via_ftp(local_file_path, remote_file_path)
                
                local_file_path = f'{LOCAL_CLASSIC_SAVES_DIR}/{game_id}/cartridge.sram.hash'
                remote_file_path = f'{CLASSIC_SAVES_DIR}/{game_id}/cartridge.sram.hash'
                if os.path.exists(local_file_path):
                    self.upload_file_via_ftp(local_file_path, remote_file_path)
                    if self.verbose:
                        print(f'[{now()}] {local_file_path} has been uploaded to {remote_file_path}.')
                #os.system(f"ftp {self.user_name}@{self.host}:{remote_path} <<< $'put {local_file_path}'")
            elif target == 'retroarch':
                file_name = self.canoe_game_id_dict[game_id]
                local_file_path = f'{LOCAL_RA_SAVES_DIR}/{file_name}.srm'
                remote_file_path = f'{RA_SAVES_DIR}/{file_name}.srm'
                # now push to retroarch directory
                if os.path.exists(local_file_path):
                    shutil.copyfile(local_file_path, remote_file_path)
                    if self.verbose:
                        print(f'[{now()}] {local_file_path} has been copied to {remote_file_path}.')
                #os.system()RA_SAVES_DIR
    
    
    def push_save_changes(self, target):
        if target == 'snes':
            while True:
                if len(self.ra_update_list) == 0:
                    break
                game_id = self.ra_update_list.pop(0)
                if game_id in self.game_id_dict.keys():
                    save_type = 'retroarch'
                elif game_id in self.canoe_game_id_dict.keys():
                    save_type = 'canoe'
                if self.verbose:
                    print(f'[{now()}] {game_id} has been updated.')
                    print(f'[{now()}] Pushing changes from Retroarch saves to SNES.')
                
                self.convert_save(game_id, target, save_type)
                self.push_save(game_id, target, save_type)
        elif target == 'retroarch':
            while True:
                if len(self.snes_update_list) == 0:
                    break
                game_id = self.snes_update_list.pop(0)
                if game_id in self.game_id_dict.keys():
                    save_type = 'retroarch'
                elif game_id in self.canoe_game_id_dict.keys():
                    save_type = 'canoe'
                if self.verbose:
                    print(f'[{now()}] {game_id} has been updated.')
                    print(f'[{now()}] Pushing changes from SNES saves to Retroarch.')
                
                self.convert_save(game_id, target, save_type)
                self.push_save(game_id, target, save_type)
    
    def perserve_icloud_folders(self):
        if sys.platform == 'darwin':
            if self.verbose:
                print(f'[{now()}] Preserving iCloud Folders...')
            os.system('shortcuts run "Preserve iCloud Folders"')
            if self.verbose:
                print(f'[{now()}] iCloud Folders are ready. Next check in {ICLOUD_TIMEOUT}mins.')
    
    # Primary run
    def start(self):
        self.notify(title='RetroSync Startup', message=f'Now starting Data Sync...')
        
        RUNNING = False
        
        time_in = time.time()
        initial_time = time_in
        while True:
            
            if self.terminate:
                self.notify(title='RetroSync Offline', message=f'Data Sync has been haulted.')
                if self.verbose:
                    print(f"[{now()}] RetroSync has been shutdown.")
                break
            
            if self.using_icloud and sys.platform == 'darwin':
                time_out = time.time()-time_in
                if time_in == initial_time and not self.has_restarted:
                    if self.verbose:
                        print(f'[{now()}] Preserving iCloud Folders... (will be ran in background next time)')
                    os.system('shortcuts run "Preserve iCloud Folders"')
                    if self.verbose:
                        print(f'[{now()}] iCloud Folders are ready. Next check in {ICLOUD_TIMEOUT}hrs.')
                    time_in = time.time()
                elif time_out > ICLOUD_TIMEOUT*60*60:
                    self.background_thread(self.perserve_icloud_folders, [])
                    time_in = time.time()
            
            #else:
            #    self.notify(title='Test', message=f'iCloud has been disabled')
            
            if self.verbose:
                print(f'[{now()}] Searching for SNES Classic on local network.')
            if self.check_connection():
                if not RUNNING:
                    self.notify(title='RetroSync Online', message=f'SNES Classic is online!')
                    RUNNING = True
                if self.verbose:
                    print(f'[{now()}] SNES Classic is online!')
                    print(f'[{now()}] Pulling Retroarch saves to temporary local directory...')
                self.pull_saves(target='retroarch') # pulls to temporary directory
                
                # Update save files within the local directory from the tempoarary directory.
                # This also generates a list of titles that have been changed on the SNES side
                if self.verbose:
                    print(f'[{now()}] Updating local retroarch saves from temporary directory...')
                self.update_local_saves(target='retroarch', save_type='canoe')
                self.update_local_saves(target='retroarch')
                
                if self.verbose:
                    print(f'[{now()}] Pulling SNES Classic saves to temporary local directory...')
                self.pull_saves(target='snes') # pulls to temporary directory
                if self.verbose:
                    print(f'[{now()}] Pulling Meta data from SNES/local for Game ID Dictionary...')
                self.generate_game_id_dicts()
                
                if self.verbose:
                    pprint(self.game_id_dict)
                    pprint(self.canoe_game_id_dict)
                
                # Update save files within the local directory from the tempoarary directory.
                # This also generates a list of titles that have been changed on the SNES side
                if self.verbose:
                    print(f"[{now()}] Updating local snes saves from temporary directory...")
                self.update_local_saves(target='snes', save_type='canoe')
                self.update_local_saves(target='snes')
                
                if self.using_modifications:
                    # Push snes save changes to retroarch
                    
                    #self.push_save_changes(target='retroarch', save_type='canoe')
                    self.push_save_changes(target='retroarch')
                    
                    # Push retroarch save changes to snes
                    #self.push_save_changes(target='snes', save_type='canoe')
                    self.push_save_changes(target='snes')
                
                
                if self.verbose:
                    print(f'[{now()}] Checking for changes again in {TIMEOUT}s.')
                time.sleep(TIMEOUT)
            
            else:
                if RUNNING:
                    self.notify(title='RetroSync Offline', message=f'SNES Classic is currently unavailable.')
                    RUNNING = False
                if self.verbose:
                    print(f"[{now()}] SNES Classic is currently unavailable.")
                time.sleep(5)
            



if __name__ == '__main__':
    retro_sync = RetroSync()
    retro_sync.verbose = True
    while True:
        try:
            retro_sync.start()
        except Exception as e:
            print(f'[{now()}] ERROR:', e)
        retro_sync.has_restarted = True
        
        if retro_sync.terminate:
            break
        
        time.sleep(5)
