import sys
import time
import json
import glob
import traceback
from hx711 import HX711

from .restapi import RestApi
from .display import Display
from .config import Config
from .sensor import Sensor
import hoplite.utils as utils


class Keg():
    
    def __init__(self, sensor, channel):
        self.sensor = sensor
        self.channel = channel
        self.name = None
        self.size = None
        self.tare_wt = None
        self.net_wt = None


    def get_weight(self):
        return self.sensor.get_weight_channel(self.channel)


    def tare(self):
        self.sensor.tare_channel(self.channel)


    def calibrate(self):
        self.sensor.calibrate_channel(self.channel)


    def get_name(self):
        return self.name


    def set_name(self, name):
        self.name = name


    def get_size(self):
        return (self.size, self.tare_wt, self.net_wt)


    def set_size(self, size, tare_wt=None, net_wt=None):
        pass
