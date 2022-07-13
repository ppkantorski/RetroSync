__author__ = "Patrick Kantorski"
__version__ = "1.0.4"
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

# Install ftpretty if not already installed
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
os.chdir(script_path); sys.path.append(script_path)

import config as cfg

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

# Target directory for retroarch saves
RA_SAVES_DIR = cfg.RA_SAVES_DIR
RA_STOCK_GAMES_DIR = cfg.RA_STOCK_GAMES_DIR

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
        self.snes_classic_ip = cfg.snes_classic_ip
        self.snes_classic_port = 22
        
        # Initialize
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
        self.disable_modifications = False
        
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
            print(f'[{now()}] RetroArch Saves directory is empty.')
            print(f'[{now()}] Saves will be populated from SNES.')
    
    # For making object run in background
    def background_thread(self, target, args_list):
        args = ()
        for i in range(len(args_list)):
            args = args + (args_list[i],)
        pr = threading.Thread(target=target, args=args)
        pr.daemon = True
        pr.start()
        return pr
    
    def notify(self, title, text):
        # Notifications are currenly only working on macOS
        if sys.platform == 'darwin':
            self.background_thread(self.notify_command, [title, text])
    
    def notify_command(self, title, text):
        os.system("""
                  osascript -e 'display notification "{}" with title "{}"'
                  """.format(text, title))
    
    def check_connection(self):
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
        game_names = [x.lower() for x in STOCK_GAME_ID_DICT.values()]
        file_names = [os.path.splitext(x)[0].lower() for x in os.listdir(RA_STOCK_GAMES_DIR)]
        
        actual_file_names = [os.path.splitext(x)[0] for x in os.listdir(RA_STOCK_GAMES_DIR)]
        
        for i in range(len(game_names)):
            game_name = game_names[i]
            closest_match = difflib.get_close_matches(game_name, file_names, n=1, cutoff=0.4)[0]
            if len(closest_match) > 0:
                index = file_names.index(closest_match)
                self.canoe_game_id_dict[game_ids[i]] = actual_file_names[index].lstrip('.')
            else:
                print(f'{STOCK_GAME_ID_DICT.values()[i]} could not be found')
        #pprint(self.canoe_game_id_dict)
    
    
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
                print(f'[{now()}] Retroarch save for {file_name} has been overwritten by classic save.')
                self.notify(title='RetroSync Overwrite', text=f'Retroarch save for {file_name} has been overwritten by Classic save.')
            elif target == 'snes':
                shutil.copyfile(f'{LOCAL_RA_SAVES_DIR}/{file_name}.srm', f'{LOCAL_CLASSIC_SAVES_DIR}/{game_id}/cartridge.sram')
                self.notify(title='RetroSync Overwrite', text=f'Classic save for {file_name} has been overwritten by Retroarch save.')
                print(f'[{now()}] Classic save for {file_name} has been overwritten by retroarch save.')
        elif save_type == 'canoe':
            file_name = self.canoe_game_id_dict[game_id]
            if target == 'retroarch':
                #shutil.copyfile(f'{LOCAL_CLASSIC_SAVES_DIR}/{game_id}/cartridge.sram', f'{LOCAL_RA_SAVES_DIR}/{file_name}.srm') # copy and convert
                from_file = f'{LOCAL_CLASSIC_SAVES_DIR}/{game_id}/cartridge.sram'
                to_file = f'{LOCAL_RA_SAVES_DIR}/{file_name}.srm'
                self.convert_save_to_retroarch(from_file, to_file)
                self.notify(title='RetroSync Overwrite', text=f'Retroarch save for {file_name} has been overwritten by Classic save.')
                print(f'[{now()}] Retroarch save for {file_name} has been overwritten by classic save.')
            elif target == 'snes':
                from_file = f'{LOCAL_RA_SAVES_DIR}/{file_name}.srm'
                to_dir = f'{LOCAL_CLASSIC_SAVES_DIR}/{game_id}'
                self.convert_save_to_canoe(from_file, to_dir, game_id)
                #shutil.copyfile(from_file, to_file)
                self.notify(title='RetroSync Overwrite', text=f'Classic save for {file_name} has been overwritten by Retroarch save.')
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
                    print(f'[{now()}] Retroarch save for {file_name} has been overwritten by Classic save.')
            elif target == 'snes':
                # Copy saves to local directory (backup too)
                for game_id in self.game_id_dict.keys():
                    file_name = self.game_id_dict[game_id]
                    shutil.copyfile(f'{LOCAL_RA_SAVES_DIR}/{file_name}.srm', f'{LOCAL_CLASSIC_SAVES_TMP_DIR}/{game_id}/cartridge.sram')
                    shutil.copyfile(f'{LOCAL_RA_SAVES_DIR}/{file_name}.srm', f'{LOCAL_CLASSIC_SAVES_DIR}/{game_id}/cartridge.sram')
                    print(f'[{now()}] Classic save for {file_name} has been overwritten by Retroarch save.')
        elif save_type == 'canoe':
            if target == 'retroarch':
                # Copy saves to local directory (backup too)
                for game_id in self.canoe_game_id_dict.keys():
                    file_name = self.canoe_game_id_dict[game_id]
                    
                    from_file = f'{LOCAL_CLASSIC_SAVES_DIR}/{game_id}/cartridge.sram'
                    with open(from_file, 'rb') as smfile:
                        srm_data = srmfile.read()
                    
                    self.convert_save_to_retroarch(from_file, f'{LOCAL_RA_SAVES_TMP_DIR}/{file_name}.srm')
                    self.convert_save_to_retroarch(from_file, f'{LOCAL_RA_SAVES_DIR}/{file_name}.srm')
                    
                    #shutil.copyfile(f'{LOCAL_CLASSIC_SAVES_DIR}/{game_id}/cartridge.sram', f'{LOCAL_RA_SAVES_TMP_DIR}/{file_name}.srm') # copy and convert
                    #shutil.copyfile(f'{LOCAL_CLASSIC_SAVES_DIR}/{game_id}/cartridge.sram', f'{LOCAL_RA_SAVES_DIR}/{file_name}.srm') # copy and convert
                    print(f'[{now()}] Retroarch save for {file_name} has been overwritten by Classic save.')
            elif target == 'snes':
                # Copy saves to local directory (backup too)
                for game_id in self.canoe_game_id_dict.keys():
                    file_name = self.canoe_game_id_dict[game_id]
                    #shutil.copyfile(f'{LOCAL_RA_SAVES_DIR}/{file_name}.srm', f'{LOCAL_CLASSIC_SAVES_TMP_DIR}/{game_id}/cartridge.sram')
                    #shutil.copyfile(f'{LOCAL_RA_SAVES_DIR}/{file_name}.srm', f'{LOCAL_CLASSIC_SAVES_DIR}/{game_id}/cartridge.sram')
                    from_file = f'{LOCAL_RA_SAVES_DIR}/{file_name}.srm'
                    self.convert_save_to_canoe(from_file, f'{LOCAL_CLASSIC_SAVES_DIR}/{game_id}')
                    self.convert_save_to_canoe(from_file, f'{LOCAL_CLASSIC_SAVES_TMP_DIR}/{game_id}')
                    
                    print(f'[{now()}] Classic save for {file_name} has been overwritten by Retroarch save.')
    
    def push_save(self, game_id, target, save_type='retroarch'):
        if save_type == 'retroarch':
            if target == 'snes':
                local_file_path = f'{LOCAL_CLASSIC_SAVES_DIR}/{game_id}/cartridge.sram'
                remote_file_path = f'{CLASSIC_SAVES_DIR}/{game_id}/cartridge.sram'
                if os.path.exists(local_file_path):
                    self.upload_file_via_ftp(local_file_path, remote_file_path)
                    print(f'[{now()}] {local_file_path} has been uploaded to {remote_file_path}.')
                #os.system(f"ftp {self.user_name}@{self.host}:{remote_path} <<< $'put {local_file_path}'")
            elif target == 'retroarch':
                file_name = self.game_id_dict[game_id]
                local_file_path = f'{LOCAL_RA_SAVES_DIR}/{file_name}.srm'
                remote_file_path = f'{RA_SAVES_DIR}/{file_name}.srm'
                # now push to retroarch directory
                if os.path.exists(local_file_path):
                    shutil.copyfile(local_file_path, remote_file_path)
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
                    print(f'[{now()}] {local_file_path} has been uploaded to {remote_file_path}.')
                #os.system(f"ftp {self.user_name}@{self.host}:{remote_path} <<< $'put {local_file_path}'")
            elif target == 'retroarch':
                file_name = self.canoe_game_id_dict[game_id]
                local_file_path = f'{LOCAL_RA_SAVES_DIR}/{file_name}.srm'
                remote_file_path = f'{RA_SAVES_DIR}/{file_name}.srm'
                # now push to retroarch directory
                if os.path.exists(local_file_path):
                    shutil.copyfile(local_file_path, remote_file_path)
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
                print(f'[{now()}] {game_id} has been updated.')
                print(f'[{now()}] Pushing changes from SNES saves to Retroarch.')
                
                self.convert_save(game_id, target, save_type)
                self.push_save(game_id, target, save_type)
    
    
    # Primary run
    def start(self):
        
        RUNNING = False
        TIMEOUT = 3 # check every X seconds
        while True:
            
            print(f'[{now()}] Searching for SNES Classic on local network.')
            if self.check_connection():
                if not RUNNING:
                    self.notify(title='RetroSync Online', text=f'SNES Classic is online!')
                    RUNNING = True
                print(f'[{now()}] SNES Classic is online!')
                
                print(f'[{now()}] Pulling Retroarch saves to temporary local directory...')
                self.pull_saves(target='retroarch') # pulls to temporary directory
                # Update save files within the local directory from the tempoarary directory.
                # This also generates a list of titles that have been changed on the SNES side
                print(f'[{now()}] Updating local retroarch saves from temporary directory...')
                self.update_local_saves(target='retroarch', save_type='canoe')
                self.update_local_saves(target='retroarch')
                
                
                print(f'[{now()}] Pulling SNES Classic saves to temporary local directory...')
                self.pull_saves(target='snes') # pulls to temporary directory
                print(f'[{now()}] Pulling Meta data from SNES/local for Game ID Dictionary...')
                self.generate_game_id_dicts()
                
                pprint(self.game_id_dict)
                pprint(self.canoe_game_id_dict)
                
                # Update save files within the local directory from the tempoarary directory.
                # This also generates a list of titles that have been changed on the SNES side
                print(f"[{now()}] Updating local snes saves from temporary directory...")
                self.update_local_saves(target='snes', save_type='canoe')
                self.update_local_saves(target='snes')
                
                if not self.disable_modifications:
                    # Push snes save changes to retroarch
                    
                    #self.push_save_changes(target='retroarch', save_type='canoe')
                    self.push_save_changes(target='retroarch')
                    
                    # Push retroarch save changes to snes
                    #self.push_save_changes(target='snes', save_type='canoe')
                    self.push_save_changes(target='snes')
                
                print(f'[{now()}] Checking for changes again in {TIMEOUT}s.')
                time.sleep(TIMEOUT)
            
            else:
                if RUNNING:
                    self.notify(title='RetroSync Offline', text=f'SNES Classic is currently unavailable.')
                    RUNNING = False
                print(f"[{now()}] SNES Classic is currently unavailable.")
                time.sleep(5)
            



if __name__ == '__main__':
    retro_sync = RetroSync()
    while True:
        try:
            retro_sync.start()
        except Exception as e:
            print(f'[{now()}]', e)
        time.sleep(5)
