from os.path import exists, expanduser
import  os
from configobj import *


class GsConfig:
    config : ConfigObj = None
    def __init__(self, product):
        self.product = product
        self.repo = f'/{product}/'
        self.baseRepo = expanduser('~') + self.repo
        self.config = ConfigObj(self.baseRepo + product + '.ini')
        if len(self.config.items()) == 0:
            self.config.write()


    def get(self, param, section=None, default=None):
        if section is not None:
            if self.config[section][param] is not None:
                return self.config[section][param]
            else:
                return default
        else:
            if self.config[param] is not None:
                return self.config[param]
            else:
                return default

    def put(self, param, value, section=None):
        if section is not None:
            if self.config.get(section) is None:
                self.sonfig[section] = {}
            self.config[section][param] = value
            self.config.write()
        else:
            self.config[param] = value
            self.config.write()
        return

    def display(self):
        for x, y in self.config.items():
            print(x, y)


gsConfig = GsConfig('gsgui')

if __name__ == "__main__":
    gsConfig.display()
