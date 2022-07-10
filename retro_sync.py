__author__ = "Patrick Kantorski"
__version__ = "1.0.0"
__maintainer__ = "Patrick Kantorski"
__status__ = "Development Build"

import filecmp
import json
import shutil 
import os, sys
import time
import datetime as dt
from pprint import pprint
import socket
from ftpretty import ftpretty
from stat import S_ISDIR, S_ISREG


# Define script path
script_path = os.path.dirname(os.path.abspath( __file__ ))
os.chdir(script_path); sys.path.append(script_path)

import config as cfg


RETRO_SYNC_DIR = script_path

# Where data is being stored locally for SNES classic for use with Retro Cloud
LOCAL_CLASSIC_SAVES_TMP_DIR = f'{RETRO_SYNC_DIR}/save_data/snes_mini/.tmp/saves'
LOCAL_CLASSIC_SAVES_DIR = f'{RETRO_SYNC_DIR}/save_data/snes_mini/saves'
LOCAL_CLASSIC_META_DIR = f'{RETRO_SYNC_DIR}/save_data/snes_mini/meta'

# Where data is being stored locally for RetroArch for use with Retro Cloud
LOCAL_RA_SAVES_TMP_DIR = f'{RETRO_SYNC_DIR}/save_data/retroarch/.tmp/saves'
LOCAL_RA_SAVES_DIR = f'{RETRO_SYNC_DIR}/save_data/retroarch/saves'

# Define SNES Classic Saves / Games directory (on device itself)
CLASSIC_SAVES_DIR = '/var/lib/clover/profiles/0'
CLASSIC_GAMES_DIR = '/var/lib/hakchi/games/snes-usa/.storage'
#CLASSIC_SAVES_DIR = f'{RETRO_SYNC_DIR}/test_data/saves'
#CLASSIC_GAMES_DIR = f'{RETRO_SYNC_DIR}/test_data/storage'

# Target directory for retroarch saves
RA_SAVES_DIR = cfg.RA_SAVES_DIR


class ftpretty_mod(ftpretty):
    def __init__(self, *args):
        ftpretty.__init__(self, *args)
    
    def get_tree_extension(self, remote, local, extension):
        """ Recursively download a directory tree.
        """
        remote = remote.replace('\\', '/')
        for entry in self.list(remote, extra=True):
            name = entry['name']
            remote_path = os.path.join(remote, name)
            local_path = os.path.join(local, name)
            if entry.flags == 'd':
                if not os.path.exists(local_path):
                    os.mkdir(local_path)
                self.get_tree_extension(remote_path, local_path, extension)
            elif entry.flags == '-':
                if extension in remote_path:
                    self.get(remote_path, local_path)
            else:
                pass

class RetroSync(object):
    def __init__(self):
        # Server Presets
        self.user_name = cfg.user_name
        self.password = cfg.password
        self.snes_classic_ip = cfg.snes_classic_ip
        self.snes_classic_port = cfg.snes_classic_port
        
        # Initialize
        #elf.ftp = None
        self.sftp = None
        #self.transport = None
        self.game_id_list = []
        self.game_id_dict = {}
        self.snes_update_list = []
        self.ra_update_list = []
        
        # Safety Presets
        self.disable_modifications = False
        
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
    
    
    def connect_to_sftp(self):
        
        #self.transport = paramiko.Transport((self.snes_classic_ip, self.snes_classic_port))
        #self.transport.connect(username = self.user_name, password = self.password)
        #self.sftp = paramiko.SFTPClient.from_transport(self.transport)
        
        self.sftp = ftpretty_mod(self.snes_classic_ip, self.user_name, self.password)
    
    
    def disconnect_from_sftp(self):
        if not (self.sftp is None):
            self.sftp.close()
        #if not (self.transport is None):
        #    self.transport.close()
    
    
    def upload_file_via_sftp(self, from_path, to_path):
        
        #from_dir = os.path.basename(from_path)
        #os.system(f'chown ppkantorski:staff {from_dir}')
        #from_dir = from_path.replace('/cartridge.sram', '')
        #os.chdir(from_dir)
        self.connect_to_sftp()
        
        self.sftp.cd(to_path)
        self.sftp.delete('cartridge.sram')
        self.sftp.put(from_path, 'cartridge.sram')
        self.disconnect_from_sftp()
    
    def download_file_via_sftp(self, from_path, to_path):
        self.connect_to_sftp()
        try:
            self.sftp.get(from_path, to_path)
        except:
            pass
        self.disconnect_from_sftp()
    
    def download_dir_via_sftp(self, from_path, to_path):
        self.connect_to_sftp()
        self.sftp.get_tree_extension(from_path, to_path, '.sram')
        #self.sftp_get_recursive(from_path, to_path)
        self.disconnect_from_sftp()
    
    
    #def sftp_get_recursive(self, from_path, to_path):
    #    if not (self.sftp is None):
    #        item_list = self.sftp.listdir_attr(from_path)
    #        to_path = str(to_path)
    #        if not os.path.isdir(to_path):
    #            os.makedirs(to_path, exist_ok=True)
    #        for item in item_list:
    #            mode = item.st_mode
    #            if S_ISDIR(mode):
    #                self.sftp_get_recursive(from_path + "/" + item.filename, to_path + "/" + item.filename)
    #            else:
    #                self.sftp.get(from_path + "/" + item.filename, to_path + "/" + item.filename)
    
    
    
    def copy_and_overwrite(self, from_path, to_path):
        if os.path.exists(to_path):
            shutil.rmtree(to_path)
        shutil.copytree(from_path, to_path)
    
    def pull_saves(self, target):
        if target == 'snes':
            # Download saves on SNES Classic to temp directory
            if os.path.exists(LOCAL_CLASSIC_SAVES_TMP_DIR):
                shutil.rmtree(LOCAL_CLASSIC_SAVES_TMP_DIR)
            os.mkdir(LOCAL_CLASSIC_SAVES_TMP_DIR)
            self.download_dir_via_sftp(CLASSIC_SAVES_DIR, LOCAL_CLASSIC_SAVES_TMP_DIR)
            #os.system(f'scp -r {self.user_name}@{self.snes_classic_ip}:{CLASSIC_SAVES_DIR} {LOCAL_CLASSIC_SAVES_TMP_DIR}')
        elif target == 'retroarch':
            # Copy saves from Retroarch to temp directory
            self.copy_and_overwrite(RA_SAVES_DIR, LOCAL_RA_SAVES_TMP_DIR)
            #os.system(f'scp -r {self.user_name}@{self.snes_classic_ip}:{CLASSIC_SAVES_DIR} {LOCAL_CLASSIC_SAVES_TMP_DIR}')
    
    
    def update_local_saves(self, target):
        if target == 'snes':
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
    
    def generate_game_id_dict(self):
        # Generate list of game IDs from classic tmp dir
        self.game_id_list = [k for k in os.listdir(LOCAL_CLASSIC_SAVES_TMP_DIR) if 'CLV' in k and 'CLV-P' not in k]
        
        
        self.game_id_dict = {}
        for game_id in self.game_id_list:
            remote_file = f'{CLASSIC_GAMES_DIR}/{game_id}/metadata.json'
            local_file = f'{LOCAL_CLASSIC_META_DIR}/{game_id}.json'
            
            if not os.path.exists(local_file):
                #os.system(f'sftp {self.user_name}@{self.snes_classic_ip}:{remote_file} {local_file}')
                self.download_file_via_sftp(remote_file, local_file)
                #self.download_file_via_ftp(remote_file, local_file)
            try:
                # Read game name from meta data
                with open(local_file) as json_file:
                    meta_data = json.load(json_file)
                self.game_id_dict[game_id] = meta_data['OriginalFilename'].rsplit(".", 1)[0]
            except:
                pass
            #if meta_data['System'] == 'Nintendo - Game Boy Advance':
            #    game_id_dict[game_id] = game_id_dict[game_id].rsplit( ".", 1 )[ 0 ]
        
        self.game_id_list = list(self.game_id_dict.keys())
    
    # target: 'retroarch' or 'snes'
    def convert_save(self, game_id, target):
        file_name = self.game_id_dict[game_id]
        if target == 'retroarch':
            shutil.copyfile(f'{LOCAL_CLASSIC_SAVES_DIR}/{game_id}/cartridge.sram', f'{LOCAL_RA_SAVES_DIR}/{file_name}.srm') # copy and convert
            print(f'Retroarch save for {file_name} has been overwritten by classic save.')
        elif target == 'snes':
            shutil.copyfile(f'{LOCAL_RA_SAVES_DIR}/{file_name}.srm', f'{LOCAL_CLASSIC_SAVES_DIR}/{game_id}/cartridge.sram')
            print(f'Classic save for {file_name} has been overwritten by retroarch save.')
    
    # target: 'retroarch' or 'snes'
    def convert_saves(self, target):
        if target == 'retroarch':
            # Copy saves to local directory (backup too)
            for game_id in self.game_id_dict.keys():
                file_name = self.game_id_dict[game_id]
                shutil.copyfile(f'{LOCAL_CLASSIC_SAVES_DIR}/{game_id}/cartridge.sram', f'{LOCAL_RA_SAVES_TMP_DIR}/{file_name}.srm') # copy and convert
                shutil.copyfile(f'{LOCAL_CLASSIC_SAVES_DIR}/{game_id}/cartridge.sram', f'{LOCAL_RA_SAVES_DIR}/{file_name}.srm') # copy and convert
                print(f'Retroarch save for {file_name} has been overwritten by classic save.')
        elif target == 'snes':
            # Copy saves to local directory (backup too)
            for game_id in self.game_id_dict.keys():
                file_name = self.game_id_dict[game_id]
                shutil.copyfile(f'{LOCAL_RA_SAVES_DIR}/{file_name}.srm', f'{LOCAL_CLASSIC_SAVES_TMP_DIR}/{game_id}/cartridge.sram')
                shutil.copyfile(f'{LOCAL_RA_SAVES_DIR}/{file_name}.srm', f'{LOCAL_CLASSIC_SAVES_DIR}/{game_id}/cartridge.sram')
                print(f'Classic save for {file_name} has been overwritten by retroarch save.')
    
    def push_save(self, game_id, target):
        if target == 'snes':
            local_file_path = f'{LOCAL_CLASSIC_SAVES_DIR}/{game_id}/cartridge.sram'
            remote_path = f'{CLASSIC_SAVES_DIR}/{game_id}'
            self.upload_file_via_sftp(local_file_path, remote_path)
            print(f'{local_file_path} has been uploaded to {remote_path}.')
            #os.system(f"sftp {self.user_name}@{self.host}:{remote_path} <<< $'put {local_file_path}'")
        elif target == 'retroarch':
            file_name = self.game_id_dict[game_id]
            local_file_path = f'{LOCAL_RA_SAVES_DIR}/{file_name}.srm'
            remote_file_path = f'{RA_SAVES_DIR}/{file_name}.srm'
            # now push to retroarch directory
            shutil.copyfile(local_file_path, remote_file_path)
            print(f'{local_file_path} has been copied to {remote_file_path}.')
            #os.system()RA_SAVES_DIR
    
    def push_save_changes(self, target):
        
        if target == 'snes':
            while True:
                if len(self.ra_update_list) == 0:
                    break
                game_id = self.ra_update_list.pop(0)
                print(f'{game_id} has been updated.')
                self.convert_save(game_id, target)
                self.push_save(game_id, target)
        elif target == 'retroarch':
            while True:
                if len(self.snes_update_list) == 0:
                    break
                game_id = self.snes_update_list.pop(0)
                print(f'{game_id} has been updated.')
                self.convert_save(game_id, target)
                self.push_save(game_id, target)
    
    # Primary run
    def start(self):
        
        TIMEOUT = 30 # check every 30 seconds
        while True:
            print(f'[{dt.datetime.now()}] Pulling Retroarch saves to temporary local directory...')
            self.pull_saves(target='retroarch') # pulls to temporary directory
            # Update save files within the local directory from the tempoarary directory.
            # This also generates a list of titles that have been changed on the SNES side
            print(f'[{dt.datetime.now()}] Updating local retroarch saves from temporary directory...')
            self.update_local_saves(target='retroarch')
            
            
            if self.check_connection():
                print(f'[{dt.datetime.now()}] SNES Classic is online!')
                
                print(f'[{dt.datetime.now()}] Pulling SNES saves to temporary local directory...')
                self.pull_saves(target='snes') # pulls to temporary directory
                print(f'[{dt.datetime.now()}] Pulling Meta data from SNES to generate Game ID Dictionary...')
                self.generate_game_id_dict()
                
                pprint(self.game_id_dict)
                
                # Update save files within the local directory from the tempoarary directory.
                # This also generates a list of titles that have been changed on the SNES side
                print(f"[{dt.datetime.now()}] Updating local snes saves from temporary directory...")
                self.update_local_saves(target='snes')
                
                if not self.disable_modifications:
                    # Push snes save changes to retroarch
                    print(f'[{dt.datetime.now()}] Pushing changes from SNES saves to Retroarch.')
                    self.push_save_changes(target='retroarch')
                    
                    # Push retroarch save changes to snes
                    print(f'[{dt.datetime.now()}] Pushing changes from Retroarch saves to SNES.')
                    self.push_save_changes(target='snes')
            
            else:
                print(f"[{dt.datetime.now()}] SNES Classic is currently unavailable.")
            
            
            print('')
            time.sleep(TIMEOUT)


if __name__ == '__main__':
    retro_sync = RetroSync()
    retro_sync.start()
