import RPi.GPIO as GPIO
import sys
import time
import json
import glob
import traceback
from hx711 import HX711

import threading
from .restapi import RestApi
from .display import Display
from .config import Config
import hoplite.utils as utils

class Hoplite():
    
    def __init__(self, debug=False):
        # debug flag - this should be first
        self.debug = debug
        utils.debug_msg(self, "init start")

        # while true, run update loop
        self.updating = False

        # config file location
        self.config_file = None

        # temperature sensor output
        # TODO: evaluate if this can be replaced by read_temp()
        self.temp = 0.0

        utils.debug_msg(self, "init end")


    def runtime_init(self):
        # All the stuff needed for runtime lives here so the Hoplite class
        # can be imported into other things for stuff like loading configs
        # without breaking GPIO access, etc.
        utils.debug_msg(self, "runtime init start")

        # dictionary containing current shared data
        self.ShData = dict()

        # dict containing current config
        self.config = Config(self.config_file, debug=self.debug)

        # list of handles for all keg HX711's found in config
        self.hx_handles = list()

        # co2 weights are a list now, could be multiple co2 cylinders
        self.co2_w = list()

        # REST API class
        self.api = RestApi(self)

        # output display
        try:
            self.display = Display(self, self.config.get('display'))
        except KeyError:
            utils.debug_msg(self, "Display not found in config, using default st7735")
            self.display = Display(self, 'st7735')

        utils.debug_msg(self, "runtime init end")


    def init_hx711(self, hx_conf):
        utils.debug_msg(self, "init hx711 start")
        dout = int(hx_conf['dout'])
        pd_sck = int(hx_conf['pd_sck'])

        try:
            offset_A = hx_conf['channels']['A']['offset']
            refunit_A = hx_conf['channels']['A']['refunit']
        except (ValueError, KeyError):
            offset_A = None
            refunit_A = None
        try:
            offset_B = hx_conf['channels']['B']['offset']
            refunit_B = hx_conf['channels']['B']['refunit']
        except (ValueError, KeyError):
            offset_B = None
            refunit_B = None

        hx = HX711(dout, pd_sck)
        hx.set_reading_format("MSB", "MSB")
        hx.reset()

        if refunit_A is not None and offset_A is not None: 
            try:
                hx.set_reference_unit_A(refunit_A)
            except ValueError:
                print("Bad channel A reference unit %s, using 1" % refunit_A)
                hx.set_reference_unit_A(1)
            hx.set_offset_A(offset_A)
        else:
            hx.set_reference_unit_A(1)

        if refunit_B is not None and offset_B is not None: 
            try:
                hx.set_reference_unit_B(refunit_B)
            except ValueError:
                print("Bad channel B reference unit %s, using 1" % refunit_B)
                hx.set_reference_unit_B(1)
            hx.set_offset_B(offset_B)
        else:
            hx.set_reference_unit_B(1)

        utils.debug_msg(self, "init hx711 end")
        return hx


    def hx711_read_ch(self, hx, channel):
        if channel == 'A':
            return int(hx.get_weight_A(5))
        elif channel == 'B':
            return int(hx.get_weight_B(5))
        else:
            return None

    
    def hx711_read_chA(self, hx):
        return int(hx.get_weight_A(5))

    
    def hx711_read_chB(self, hx):
        return int(hx.get_weight_B(5))


    def hx711_cal_chA(self, hx, real_w):
        ref = hx.REFERENCE_UNIT
        hx.set_reference_unit_A(1)
        raw_w = hx.get_weight_A(7)
        hx.set_reference_unit_A(ref)
        return raw_w / float(real_w)


    def hx711_cal_chB(self, hx, real_w):
        ref = hx.REFERENCE_UNIT_B
        hx.set_reference_unit_B(1)
        raw_w = hx.get_weight_B(7)
        hx.set_reference_unit_B(ref)
        return raw_w / float(real_w)


    def read_weight(self, hx):
        hx.reset()
        kegA = self.hx711_read_chA(hx)
        kegB = self.hx711_read_chB(hx)
        return ( kegA, kegB )


    def read_temp(self):
        base_dir = '/sys/bus/w1/devices/'
        try:
            device_folder = glob.glob(base_dir + '28*')[0]
            device_file = device_folder + '/temperature'
            utils.debug_msg(self, "Opening %s" % device_file)
            f = open(device_file, 'r')
            temp = f.read()
            f.close()
            utils.debug_msg(self, "Raw temp value is %s" % temp)
        except (IOError, ValueError, IndexError):
            utils.debug_msg(self, "ERROR reading temp sensor")
            temp = 0
        return int(temp)


    def read_co2(self):
        co2 = list()
        for index, hx_conf in enumerate(self.config.get('hx')):
            for channel in ['A', 'B']:
                try:
                    if hx_conf['channels'][channel]['co2'] == True:
                        local_w = self.hx711_read_ch(self.hx_handles[index], channel)
                        local_max = hx_conf['channels'][channel]['volume'] * 1000
                        local_tare = hx_conf['channels'][channel]['tare'] * 1000
                        utils.debug_msg(self, "channel %s: %s, %s, %s" % (channel, local_w, local_max, local_tare))
                        local_net_w = max((local_w - local_tare), 0)
                        local_pct = local_net_w / float(local_max)
                        co2.append(int(local_pct * 100))
                except KeyError:
                    pass
        return co2


    def cleanup(self, signum=None, frame=None):
        utils.debug_msg(self, "begin cleanup")
        self.config.save_config()
        utils.debug_msg(self, "config saved")
        for index, hx in enumerate(self.hx_handles):
            try:
                utils.debug_msg(self, "power down %s" % index)
                hx.power_down()
            except RuntimeError:
                utils.debug_msg(self, "%s already powered down" % index)
                # GPIO already cleaned up
                pass
        utils.debug_msg(self, "gpio cleanup")
        GPIO.cleanup()
        utils.debug_msg(self, "cleanup complete")


    def setup_all_kegs(self):
        self.hx_handles = list()
        # grab each keg definition from the config
        for index, hx_conf in enumerate(self.config.get('hx')):
            hx = self.init_hx711(hx_conf)
            self.hx_handles.insert(index, hx)


    def update(self):
        index = 0
        while self.updating:
            for index, hx in enumerate(self.hx_handles):
                if not self.updating: break
                utils.debug_msg(self, "index %s" % index)
                self.temp = self.read_temp()
                self.co2_w = self.read_co2()
                utils.debug_msg(self, "temp: %s co2: %s" % (self.temp, self.co2_w))
                weight = None

                if len(self.hx_handles) <= 0:
                    utils.debug_msg(self, "no sensors currently configured")
                else:
                    try:
                        mode = self.config.get('weight_mode')
                    except KeyError:
                        utils.debug_msg(self, "weight_mode not in config, using as_kg_gross")
                        mode = 'as_kg_gross'
                    try:
                        weight = self.read_weight(hx)
                        self.display.render(weight, mode, self.config.get('hx')[index])
                    except IndexError:
                        utils.debug_msg(self, traceback.format_exc())
                        utils.debug_msg(self, "index %s not present or removed during access" % index)

                try:
                    self.ShData['data']['weight'][index] = weight
                except IndexError:
                    self.ShData['data']['weight'].insert(index, weight)

                self.ShData['data']['temp'] = self.temp
                self.ShData['data']['co2'] = self.co2_w

                if self.ShData['config'] != self.config.config:
                    utils.debug_msg(self, 'config changed, save and update')
                    self.config.config = self.ShData['config']
                    self.config.save_config()
                    self.setup_all_kegs()
            time.sleep(0.1)

        utils.debug_msg(self, "updates stopped")


    def main(self, config_file='config.json', api_listen=None):
        self.config_file = config_file
        self.runtime_init()
        if self.config.config == None:
            print("No valid config, bailing out")
            sys.exit()

        utils.debug_msg(self, "debug enabled")

        self.ShData['data'] = dict()
        self.ShData['data']['weight'] = list()
        self.ShData['config'] = self.config.config

        self.setup_all_kegs()

        utils.debug_msg(self, 'api listener: %s' % api_listen)
        if api_listen != None:
            api_listen_split = api_listen.split(':')
            if len(api_listen_split) == 2:
                api_host = api_listen_split[0]
                api_port = api_listen_split[1]
            elif len(api_listen_split) == 1:
                api_host = api_listen_split[0]
                api_port = '5000'
            else:
                print('Incorrect formatting for API listen address, using defaults')
                api_host = '0.0.0.0'
                api_port = '5000'
        else:
            api_host = '0.0.0.0'
            api_port = '5000'

        print('Starting API at %s:%s' % (api_host, api_port))
        self.api_process = threading.Thread(None, self.api.worker, 'hoplite REST api', kwargs={'host': api_host, 'port': api_port})
        self.api_process.daemon=True
        self.api_process.start()

        try:
            self.updating = True
            self.update_process = threading.Thread(None, self.update, 'hoplite data collection')
            self.update_process.daemon = True
            self.update_process.start()
            while self.updating:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit, RuntimeError):
            utils.debug_msg(self, "stop updating")
            self.updating = False
            self.update_process.join(30)
            self.cleanup()
            sys.exit()


# this is here in case we get run as a standalone script
if __name__ == '__main__':
    h = Hoplite()
    h.main()
