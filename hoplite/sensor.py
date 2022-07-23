import sys
import time
import json
import glob
import traceback
from hx711 import HX711

from .restapi import RestApi
from .display import Display
from .config import Config
import hoplite.utils as utils


class Sensor():

    # Breakout board port data
    # Value is list( pd_sck, dout )
    breakout_ports = {
        1: (6, 5),
        2: (13, 12),
        3: (27, 17),
        4: (25, 22),
    }

    def __init__(self, port, pd_sck=None, dout=None):
        if port != 0:
            self.pd_sck = breakout_ports[port][0]
            self.dout = breakout_ports[port][1]
        else:
            self.pd_sck = pd_sck
            self.dout = dout


    def poll(self):
        pass


    def get_weight_channel(self, channel):
        pass


    def tare_channel(self, channel):
        pass


    def calibrate_channel(self, channel):
        pass
