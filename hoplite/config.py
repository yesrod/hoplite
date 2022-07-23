import json
import hoplite.utils as utils

class Config():
    def __init__(self, config_file="config.json", debug=False):
        self.debug = debug
        utils.debug_msg(self, "load config start")
        self.config_file = config_file
        try: 
            save = open(self.config_file, "r")
            config = json.load(save)
            save.close()
        except IOError:
            print("No config found at %s, using defaults" % self.config_file)
            config = None
        except ValueError:
            print("Config at %s has syntax issues, cannot load" % self.config_file)
            config = None
        self.config = self.build_config(config)
        utils.debug_msg(self, self.config)
        utils.debug_msg(self, "load config end")


    def save_config(self):
        try:
            save = open(self.config_file, "w")
            json.dump(self.config, save, indent=2)
            save.close()
        except IOError as e:
            print("Could not save config: %s" % e.strerror)


    def build_config(self, current_config=None):
        required = {
            'display': 'st7735', 
            'weight_mode': 'as_kg_gross',
            'hx': []
        }
        if current_config:
            for r in required.keys():
                if r not in current_config.keys():
                    current_config[r] = required[r]
            config = current_config
        else:
            config = required
        return config


    def get(self, key):
        try:
            return self.config[key]
        except KeyError:
            return None

