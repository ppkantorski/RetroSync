#!/usr/bin/env python3
__author__ = "Patrick Kantorski"
__version__ = "1.0.8"
__maintainer__ = "Patrick Kantorski"
__status__ = "Development Build"


import telegram#, emoji
from telegram.ext.updater import Updater
from telegram.update import Update
from telegram.ext.callbackcontext import CallbackContext
from telegram.ext.commandhandler import CommandHandler
from telegram.ext.messagehandler import MessageHandler
from telegram.ext.filters import Filters
from telegram.ext import CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import threading
import os, sys
import pprint
import time
import datetime as dt
import json

#from pymemcache.client import base
#memcache_client = base.Client(('localhost', 11211))

# Define script path
telegram_path = os.path.dirname(os.path.abspath( __file__ ))
sys.path.append(telegram_path)
sys.dont_write_bytecode = True



class RetroSyncTelegram(object):
    def __init__(self):
        
        self.load_config()
        
        self.bot = telegram.Bot(token=self.token)
        self.updater = Updater(token=self.token, use_context=True)
        #self.group_filter = (Filters.sender_chat(int(self.chat_id)))
        
        self.terminate = False
        self.tell_to_start = False
    
    def load_config(self):
        # load controller configurations
        load_failed = False
        if os.path.exists(f'{telegram_path}/telegram_config.json'):
            try:
                with open(f'{telegram_path}/telegram_config.json', 'r') as f:
                    self.telegram_config = json.load(f)
                
                # Telegram settings
                self.token = self.telegram_config['token']
                self.chat_id = self.telegram_config['chat_id']
                
                if len(self.token) == 0 or len(self.chat_id) == 0:
                    load_failed = True
            except:
                load_failed = True
        else:
            load_failed = True
        
        if load_failed:
            self.telegram_config = {
                "token": "",
                "chat_id": ""
            }
            self.write_config()
            
            print("Please modify 'telegram_config.json' accordingly before running again.")
            exit()
        
    
    def notify(self, message):
        self.bot.send_message(chat_id=self.chat_id, text=message)
    
    
    def write_config(self):
        with open(f'{telegram_path}/telegram_config.json', 'w') as f:
            f.write(json.dumps(self.telegram_config, sort_keys=True, indent=4))
    
    def stop(self, update: Update, context: CallbackContext):
        self.terminate = True
        self.tell_to_start = False
        #self.notify("Stop has been toggled.")
    
    def start(self, update: Update, context: CallbackContext):
        update.message.reply_text(
            f"Welcome to the RetroSync Telegram Notifier!")
        self.terminate = False
        self.tell_to_start = True
    
    #def help_control(self, update: Update, context: CallbackContext):
    #    update.message.reply_text("Available Commands :\n" +\
    #        "- /about - About RetroSync Telegram Notifier.\n" +\
    #        "- /help - View Help Page.")
    #
    #def about_control(self, update: Update, context: CallbackContext):
    #    update.message.reply_text(f"RetroSync Telegram Notifier was designed by {__author__}.\n"+
    #        f"See on GitHub https://github.com/ppkantorski/RetroSync")
    
    def unknown(self, update: Update, context: CallbackContext):
        pass
        #update.message.reply_text(
        #    "Sorry '%s' is not a valid command" % update.message.text)
    
    def unknown_text(self, update: Update, context: CallbackContext):
        pass
        #update.message.reply_text(
        #    "Sorry I can't recognize you , you said '%s'" % update.message.text)
    
    
    # Start bot
    def run(self):
        #self.updater.dispatcher.add_handler(CommandHandler('plot_data', self.plot_data, self.group_filter))
        #self.updater.dispatcher.add_handler(CommandHandler('plot', self.plot, self.group_filter))
        #self.updater.dispatcher.add_handler(CallbackQueryHandler(self.plot_menu, pattern='plot_menu'))
        #for ft_bot in self.ft_bots:
        #    self.updater.dispatcher.add_handler(CallbackQueryHandler(self.pair_plot_menu, pattern=f'{ft_bot}_plot_menu'))
        #    for pair in self.pairs[ft_bot]:
        #        self.updater.dispatcher.add_handler(CallbackQueryHandler(self.plot_response, pattern=f'{ft_bot}-{pair}_plot'))
        #self.updater.dispatcher.add_handler(CallbackQueryHandler(self.second_submenu, pattern='m2_1'))
        #self.updater.dispatcher.add_handler(CommandHandler('start', self.start))
        #self.updater.dispatcher.add_handler(CommandHandler('stop', self.stop))
        #self.updater.dispatcher.add_handler(CommandHandler('help', self.help_control))
        #self.updater.dispatcher.add_handler(CommandHandler('plot', self.plot, self.user_filter))
        #self.updater.dispatcher.add_handler(CommandHandler('indicators', self.indicators, self.group_filter))
        #self.updater.dispatcher.add_handler(CommandHandler('public_url', self.public_url, self.group_filter))
        #self.updater.dispatcher.add_handler(CommandHandler('sync_configs', self.sync_configs, self.group_filter))
        self.updater.dispatcher.add_handler(MessageHandler(Filters.text, self.unknown))
        self.updater.dispatcher.add_handler(MessageHandler(
            Filters.command, self.unknown))  # Filters out unknown commands
        
        # Filters out unknown messages.
        self.updater.dispatcher.add_handler(MessageHandler(Filters.text, self.unknown_text))
        
        self.updater.start_polling()

# For making object run in background
def background_thread(target, args_list):
    args = ()
    for arg in args_list:
        args += (arg,)
    pr = threading.Thread(target=target, args=args)
    pr.daemon = True
    pr.start()
    return pr


if __name__ == '__main__':
    retro_sync_telegram = RetroSyncTelegram()
    retro_sync_telegram.run()
