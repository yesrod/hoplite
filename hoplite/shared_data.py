import sys
import time
import json
import glob
import traceback
from hx711 import HX711

from .restapi import RestApi
from .display import Display
from .config import Config
from .keg import Keg
import hoplite.utils as utils

class SharedData():

    def __init__(self, config=None):
        if config:
            self.config = config
        else:
            self.config = Config()

        self.keg_list = []
        