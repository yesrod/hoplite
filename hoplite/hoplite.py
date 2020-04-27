from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.lcd.device import st7735
from luma.lcd.aux import backlight
import RPi.GPIO as GPIO
import sys
import time
import json
import posix_ipc
import mmap
import glob
from hx711 import HX711


class Hoplite():
    
    def __init__(self):
        # keg data dictionary
        # value is list( volume in liters, empty weight in kg )
        self.keg_data = {
            'half_bbl': (58.6, 13.6),
            'tall_qtr_bbl': (29.3, 10),
            'short_qtr_bbl': (29.3, 10),
            'sixth_bbl': (19.5, 7.5),
            'corny': (18.9, 4),
        }

        # debug flag
        self.debug = False

        # shared memory segment for communicating with web interface
        mem = posix_ipc.SharedMemory('/hoplite', flags=posix_ipc.O_CREAT, size=65536)
        self.ShMem = mmap.mmap(mem.fd, mem.size)
        mem.close_fd()

        # semaphore lock for shared memory
        self.ShLock = posix_ipc.Semaphore('/hoplite', flags=posix_ipc.O_CREAT)
        self.ShLock.release()

        # dictionary containing current shared memory data
        self.ShData = dict()

        # config file location
        self.config_file = None

        # dict containing current config
        self.config = dict()

        # output device
        self.device = None

        # canvas for output device
        self.draw = None

        # temperature sensor output
        # TODO: evaluate if this can be replaced by read_temp()
        self.temp = None

        # list of handles for all keg HX711's found in config
        self.hx_handles = list()

        # co2 weights are a list now, could be multiple co2 cylinders
        self.co2_w = list()


    def debug_msg(self, message):
        if self.debug:
            print("%s: %s" % (sys._getframe(1).f_code.co_name, message))


    def shmem_read(self, timeout=None):
        map_data = b''
        self.ShLock.acquire(timeout)
        self.ShMem.seek(0, 0)
        while True:
            line = self.ShMem.readline()
            if line == b'': break
            map_data += line.rstrip(b'\0')
        self.ShMem.seek(0, 0)
        self.ShLock.release()
        self.ShData = json.loads(map_data.decode())


    def shmem_write(self, timeout=None):
        self.ShLock.acquire(timeout)
        self.shmem_clear()
        self.ShMem.write(json.dumps(self.ShData, indent=2).encode())
        self.ShMem.flush()
        self.ShLock.release()


    def shmem_clear(self):
        zero_fill = b'\0' * (self.ShMem.size())
        self.ShMem.seek(0, 0)
        self.ShMem.write(zero_fill)
        self.ShMem.seek(0, 0)
        self.ShMem.flush()


    def init_st7735(self):
        light = backlight(gpio=GPIO, gpio_LIGHT=18, active_low=False)
        light.enable(True)
        serial = spi(port=0, device=0, gpio_DC=23, gpio_RST=24)
        device = st7735(serial)
        return device

    
    def init_hx711(self, hx_conf):
        dout = hx_conf['dout']
        pd_sck = hx_conf['pd_sck']

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

        if refunit_A: 
            hx.set_reference_unit_A(refunit_A)
            if offset_A:
                hx.set_offset_A(offset_A)
            else:
                hx.tare_A()
                self.debug_msg("channel A offset: %s" % hx.OFFSET)

        if refunit_B: 
            hx.set_reference_unit_B(refunit_B)
            if offset_B:
                hx.set_offset_B(offset_B)
            else:
                hx.tare_B()
                self.debug_msg("channel B offset: %s" % hx.OFFSET_B)

        return hx

    
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

    
    def load_config(self, config_file="config.json"):
        try: 
            save = open(config_file, "r")
            config = json.load(save)
            save.close()
        except IOError:
            print("No config found at %s, using defaults" % config_file)
            config = self.build_config()
        except ValueError:
            print("Config at %s has syntax issues, cannot load" % config_file)
            config = None
        return config

    
    def save_config(self, config, config_file="config.json"):
        try:
            save = open(config_file, "w")
            json.dump(config, save, indent=2)
            save.close()
        except IOError as e:
            print("Could not save config: %s" % e.strerror)

    
    def build_config(self):
        config = dict()
        config['weight_mode'] = 'as_kg_gross'
        config['hx'] = list()
        hx = dict()
        hx['channels'] = dict()
        hx['dout'] = 5
        hx['pd_sck'] = 6
        kegA = dict()
        kegB = dict()
        kegA['offset'] = None
        kegA['refunit'] = 21.7
        kegA['name'] = "Yuengling"
        kegA['size'] = self.keg_data['half_bbl']
        kegA['size_name'] = 'half_bbl'
        kegB['offset'] = None
        kegB['refunit'] = 5.4
        kegB['name'] = "Angry Orchard"
        kegB['size'] = self.keg_data['sixth_bbl']
        kegB['size_name'] = 'sixth_bbl'
        hx['channels']['A'] = kegA
        hx['channels']['B'] = kegB
        config['hx'].append(hx)
        co2_hx = dict()
        co2_hx['channels'] = dict()
        co2_hx['dout'] = 12
        co2_hx['pd_sck'] = 13
        co2_A = dict()
        co2_A['offset'] = None
        co2_A['refunit'] = 21.7
        co2_A['name'] = "CO2"
        co2_A['size'] = [2.27, 4.82]
        co2_A['size_name'] = "custom"
        co2_A['co2'] = True
        co2_hx['channels']['A'] = co2_A
        config['hx'].append(co2_hx)
        return config

    
    def text_header(self, y, message, fill="white"):
        W = self.device.width
        w, h = self.draw.textsize(message)
        self.draw.text(((W-w)/2, y), message, fill=fill)

    
    def text_align_center(self, x, y, message, fill="white"):
        w, h = self.draw.textsize(message)
        self.draw.text((x-(w/2), y), message, fill=fill)

    
    def fill_bar(self, x, y, min_w, max_w, w, outline="white", fill=None):
        net_w = max(w - min_w, 0)
        max_net_w = max_w - min_w
        fill_percent = float(net_w) / float(max_net_w)
        max_y = self.device.height - 21
        min_y = y+1
        max_bar = max_y - min_y
        fill_height = max(min_y, min_y + (max_bar - (max_bar * fill_percent)))

        if fill == None:
            fill = self.fill_bar_color(fill_percent)

        self.draw.rectangle([x,y, x+20,self.device.height-20], outline=outline, fill="black")
        self.draw.rectangle([x+1,fill_height, x+19,max_y], outline=fill, fill=fill)
        self.debug_msg("%s: %s" % (fill_percent, fill)) 


    def fill_bar_color(self, percent):
        if percent > 0.5:
            return "green"
        if 0.5 > percent > 0.2:
            return "yellow"
        if 0.2 > percent:
            return "red"
        # default in case something breaks
        return "gray"


    def as_kg(self, val):
        return "%s kg" % "{0:.2f}".format(val / 1000.0)


    def as_pint(self, val):
        return '%s pt.' % int(val / 473)


    def format_weight(self, val, tare=None, mode=None, cap=None):
        if mode == None:
            try:
                mode = self.config['weight_mode']
            except ( KeyError, ValueError ):
                mode = 'as_kg_gross'
                self.debug_msg('using default weight mode %s' % mode)

        if mode == 'as_kg_gross':
            return self.as_kg(val)

        elif mode == 'as_kg_net':
            if tare == None:
                raise ValueError('tare must not be None when using as_kg_net')
            else:
                return self.as_kg(val - tare)

        elif mode == 'as_pint':
            if tare == None:
                raise ValueError('tare must not be None when using as_pint')
            else:
                return self.as_pint(val - tare)

        elif mode == 'as_pct':
            if tare == None:
                raise ValueError('tare must not be None when using as_pct')
            elif max == None:
                raise ValueError('max must not be None when using as_pct')
            else:
                return "%s%%" % int(((val - tare) / cap) * 100)

        else:
            raise ValueError('bad mode %s' % mode)


    def read_weight(self, hx):
        hx.reset()
        kegA = self.hx711_read_chA(hx)
        kegB = self.hx711_read_chB(hx)
        return ( kegA, kegB )


    def render_st7735(self, weight, hx_conf):
        try:
            kegA = weight[0]
            kegA_name = hx_conf['channels']['A']['name'][0:13]
            kegA_min = hx_conf['channels']['A']['size'][1] * 1000
            kegA_cap = hx_conf['channels']['A']['size'][0] * 1000
            kegA_max = kegA_min + kegA_cap
        except (ValueError, KeyError):
            # no channel A data
            kegA = 0
            kegA_name = None
            kegA_min = 0
            kegA_cap = 0
            kegA_max = 0

        try:
            kegB = weight[1]
            kegB_name = hx_conf['channels']['B']['name'][0:13]
            kegB_min = hx_conf['channels']['B']['size'][1] * 1000
            kegB_cap = hx_conf['channels']['B']['size'][0] * 1000
            kegB_max = kegB_min + kegB_cap
        except (ValueError, KeyError):
            # no channel B data
            kegB = 0
            kegB_name = None
            kegB_min = 0
            kegB_cap = 0
            kegB_max = 0


        with canvas(self.device) as self.draw:
            self.debug_msg("%s: %s/%s  %s: %s/%s" % ( kegA_name, kegA, kegA_max, 
                                             kegB_name, kegB, kegB_max ))
            self.debug_msg("min: %s %s" % ( kegA_min, kegB_min ))
            self.debug_msg(self.as_degF(self.temp))
            self.debug_msg("CO2: "+str(self.co2_w[0])+"%") #TODO: Handle multiple CO2 sources

            self.text_header(0, "HOPLITE", fill="red")
            self.text_align_center(30, 0, self.as_degF(self.temp), fill="blue")
            self.text_align_center(130, 0, "CO2:"+str(self.co2_w[0])+"%", fill="blue")

            if kegA_name:
                self.text_align_center(40, 15, kegA_name)
                self.fill_bar(30, 35, kegA_min, kegA_max, kegA)
                self.text_align_center(40, self.device.height-10,
                                       self.format_weight(kegA, tare=kegA_min, cap=kegA_cap))

            if kegB_name:
                self.text_align_center(120, 15, kegB_name)
                self.fill_bar(110, 35, kegB_min, kegB_max, kegB)
                self.text_align_center(120, self.device.height-10,
                                       self.format_weight(kegB, tare=kegB_min, cap=kegB_cap))


    def read_temp(self):
        base_dir = '/sys/bus/w1/devices/'
        try:
            device_folder = glob.glob(base_dir + '28*')[0]
            device_file = device_folder + '/hwmon/hwmon0/temp1_input'
            f = open(device_file, 'r')
            temp = f.read()
            f.close()
        except (IOError, ValueError, IndexError):
            temp = 0
        return int(temp)


    def read_co2(self):
        co2 = list()
        for index, hx_conf in enumerate(self.config['hx']):
            try:
                if hx_conf['channels']['A']['co2'] == True:
                    local_w = self.hx711_read_chA(self.hx_handles[index])
                    local_max = hx_conf['channels']['A']['size'][0] * 1000
                    local_tare = hx_conf['channels']['A']['size'][1] * 1000
                    local_net_w = max((local_w - local_tare), 0) 
                    local_pct = local_net_w / float(local_max)
                    co2.append(local_pct)
            except KeyError:
                pass
            try:
                if hx_conf['channels']['B']['co2'] == True:
                    local_w = self.hx711_read_chB(self.hx_handles[index])
                    local_max = hx_conf['channels']['B']['size'][0]
                    local_tare = hx_conf['channels']['B']['size'][1]
                    local_net_w = max((local_w - local_tare), 0)    
                    local_pct = local_net_w / float(local_max)
                    co2.append(local_pct)
            except KeyError:
                pass
        return co2


    def as_degC(self, temp):
        return u'%s\u00b0C' % '{0:.1f}'.format(float(temp) / 1000.0)


    def as_degF(self, temp):
        real_c = float(temp) / 1000.0
        deg_f = real_c * (9.0/5.0) + 32.0
        return u'%s\u00b0F' % '{0:.1f}'.format(deg_f)


    def cleanup(self, signum=None, frame=None):
        self.debug_msg("begin cleanup")
        self.save_config(self.config, self.config_file)
        self.debug_msg("config saved")
        for index, hx in enumerate(self.hx_handles):
            try:
                self.debug_msg("power down %s" % index)
                hx.power_down()
            except RuntimeError:
                self.debug_msg("%s already powered down" % index)
                # GPIO already cleaned up
                pass
        self.debug_msg("gpio cleanup")
        GPIO.cleanup()
        self.debug_msg("shmem cleanup")
        try:
            self.ShMem.close()
            posix_ipc.unlink_shared_memory('/hoplite')
            self.ShLock.release()
            self.ShLock.unlink()
        except posix_ipc.ExistentialError:
            # shmem already cleaned up
            self.debug_msg("shmem already cleaned up")
            pass
        self.debug_msg("cleanup complete")


    def setup_all_kegs(self):
        # grab each keg definition from the config
        for index, hx_conf in enumerate(self.config['hx']):
            hx = self.init_hx711(hx_conf)
            self.hx_handles.insert(index, hx)


    def update(self):
        index = 0
        while True:
            self.temp = self.read_temp()

            self.co2_w = self.read_co2()

            weight = self.read_weight(self.hx_handles[index])
            self.debug_msg("temp: %s co2: %s" % (self.temp, self.co2_w))
            self.render_st7735(weight, self.config['hx'][index])

            self.shmem_read()
            if self.ShData['config']:
                self.config = self.ShData['config']
            try:
                self.ShData['data']['weight'][index] = weight
            except IndexError:
                self.ShData['data']['weight'].insert(index, weight)
            self.ShData['data']['temp'] = self.temp
            self.ShData['data']['co2'] = self.co2_w
            self.shmem_write()

            index += 1
            if index >= len(self.hx_handles):
                index = 0

            time.sleep(0.1)


    def main(self, config_file='config.json'):
        self.config_file = config_file
        self.config = self.load_config(self.config_file)
        if self.config == None:
            print("No valid config, bailing out")
            sys.exit()

        # compatibility fixes
        # add weight mode if absent
        if not 'weight_mode' in self.config:
            self.config['weight_mode'] = 'as_kg_gross'
            self.debug_msg('adding weight_mode = %s to config' % self.config['weight_mode'])

        self.ShData['data'] = dict()
        self.ShData['data']['weight'] = list()
        self.ShData['config'] = self.config
        self.shmem_write()

        self.device = self.init_st7735()
        self.setup_all_kegs()

        while True:
            try:
                self.update()
            except (KeyboardInterrupt, SystemExit, RuntimeError):
                self.cleanup()
                sys.exit()


# this is here in case we get run as a standalone script
if __name__ == '__main__':
    h = Hoplite()
    h.main()
