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
from .weighable import Weighable
import hoplite.utils as utils


class CO2(Weighable):

    def __init__(
        self, 
        name,
        port, 
        channel,
        offset,
        refunit,
        location = None,
        size = None,
        tare_wt = None,
        net_wt = None
    ):
        super().__init__(port, channel)
        self.weight_data = utils.co2_data
