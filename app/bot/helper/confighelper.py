import configparser
import os
from os import environ, path
from dotenv import load_dotenv

class ConfigHelper():
    _CONFIG_PATH = 'app/config/config.ini'
    _BOT_SECTION = 'bot_envs'

    # self.config is the public dictionary to get config values.
    # self._config is the private configparser object.
    config = {
        'discord_bot_token': "", 'plex_user': "", 'plex_pass': "", 'plex_token': "",
        'plex_base_url': "", 'plex_roles': "", 'plex_server_name': "", 'plex_libs': "",
        'jellyfin_api_key' : "", 'jellyfin_server_url' : "", 'jellyfin_roles' : "",
        'jellyfin_libs' : "", 'plex_enabled' : False, 'jellyfin_enabled' : False, 'jellyfin_external_url' : ""
    }

    def __init__(self):
        self._config = configparser.ConfigParser()
        if (path.exists('bot.env')):
            try:
                load_dotenv(dotenv_path='bot.env')
                # settings
                self.config["discord_bot_token"] = environ.get('discord_bot_token')
                self.discord_bot_token = self._config["discord_bot_token"]
                self.switch = 1
            except Exception as e:
                pass
        
        try:
            self.config['discord_bot_token'] = str(os.environ['token'])
            self.discord_bot_token = self.config['discord_bot_token']
            self.switch = 1
        except Exception as e:
            pass

        # Create config file if not exist
        if not (path.exists(self._CONFIG_PATH)):
            with open (self._CONFIG_PATH, 'w'):
                pass

        self.sync_config()

        
    def sync_config(self):
        print("Syncing config...")
        self._config.read(self._CONFIG_PATH)
        nonConfigured = []
        for key in self.config:
            try:
                self.config[key] = self._config.get(self._BOT_SECTION, key)
            except Exception:
                nonConfigured.append(key)
        print("Non configured keys: " + str(nonConfigured))

        # Format Plex roles list
        if self.config['plex_roles']:
            self.config['plex_roles'] = list(self.config['plex_roles'].split(','))
        else:
            self.config['plex_roles'] = []
        
        # Format Plex libs list
        if not self.config['plex_libs'] or self.config['plex_libs'] == ["all"]:
            self.config['plex_libs'] = []
        else:
            print("Plex libs: " + str(self.config['plex_libs']))
            self.config['plex_libs'] = list(self.config['plex_libs'].split(','))
        
        # Format Jellyfin roles list
        if self.config['jellyfin_roles']:
            self.config['jellyfin_roles'] = list(self.config['jellyfin_roles'].split(','))
        else:
            self.config['jellyfin_roles'] = []
        
        # Format Jellyfin libs list
        if not self.config['jellyfin_libs']:
            self.config['jellyfin_libs'] = []
        else:
            self.config['jellyfin_libs'] = list(self.config['jellyfin_libs'].split(','))

        # Format Jellyfin External URL
        if not self.config['jellyfin_external_url']:
            print("Defaulting Jellyfin external url to server URL.")
            self.config['jellyfin_external_url'] = self.config['jellyfin_server_url']

        # set flags
        self.plex_token_configured = bool(self.config['plex_token']) and bool(self.config['plex_base_url'])
        self.plex_configured = bool(self.plex_token_configured) or (
            bool(self.config['plex_user']) and bool(self.config['plex_pass']) and bool(self.config['plex_server_name'])
        )
        self.jellyfin_configured = bool(self.config['jellyfin_api_key']) and bool(self.config['jellyfin_server_url'])

        # Format enablement configs
        try:
            self.config['plex_enabled'] = self._config.getboolean(self._BOT_SECTION, 'plex_enabled')
        except Exception:
            pass

        try:
            self.config['jellyfin_enabled'] = self._config.getboolean(self._BOT_SECTION, 'jellyfin_enabled')
        except Exception:
            pass


    
    def write_config(self, key, value, resync = True):
        value = str(value)
        try:
            self._config.read(self._CONFIG_PATH)
        except Exception as e:
            print(e)
            print("Cannot Read Config File")
        
        try:
            self._config.set(self._BOT_SECTION, key, value)
        except Exception as e:
            print (e)
            self._config.add_section(self._BOT_SECTION)
            self._config.set(self._BOT_SECTION, key, value)
        
        try:
            with open(self._CONFIG_PATH, 'w') as configfile:
                self._config.write(configfile)
            self.config[key] = value
        except Exception as e:
            print(e)
            print("Cannot Write Config File")
        if resync:
            self.sync_config()

