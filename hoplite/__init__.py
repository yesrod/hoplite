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
    # keg data dictionary
    global keg_data
    
    # config
    global config

    # output device and draw handle
    global device
    global draw

    # list of all keg HX711's detected
    global hx_handles

    # one special HX711 for CO2
    global co2
    global co2_w

    # temperature sensor output
    global temp

    # shared memory segment for communicating with web interface,
    # semaphore lock, and data to be shared
    global ShMem
    global ShLock
    global ShData

    # config file location
    global config_file

    # debug flag
    global debug

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

        self.debug = False

        mem = posix_ipc.SharedMemory('/hoplite', flags=posix_ipc.O_CREAT, size=65536)
        self.ShMem = mmap.mmap(mem.fd, mem.size)
        mem.close_fd()

        self.ShLock = posix_ipc.Semaphore('/hoplite', flags=posix_ipc.O_CREAT)
        self.ShLock.release()


    def debug_msg(self, message):
        if self.debug:
            print message


    def shmem_read(self, timeout=None):
        map_data = ''
        self.ShLock.acquire(timeout)
        self.ShMem.seek(0, 0)
        while True:
                line = self.ShMem.readline()
                if line == '': break
                map_data += line.rstrip('\0')
        self.ShMem.seek(0, 0)
        self.ShLock.release()
        self.ShData = json.loads(map_data)


    def shmem_write(self, timeout=None):
        self.ShLock.acquire(timeout)
        self.shmem_clear()
        self.ShMem.write(json.dumps(self.ShData, indent=2))
        self.ShMem.flush()
        self.ShLock.release()


    def shmem_clear(self):
        zero_fill = '\0' * (self.ShMem.size())
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
        hx.set_reading_format("LSB", "MSB")
        hx.reset()

        if refunit_A: 
            hx.set_reference_unit_A(refunit_A)
            if offset_A:
                hx.set_offset_A(offset_A)
            else:
                hx.tare_A()
                self.debug_msg("channel A offset: %s" % hx.OFFSET_A)

        if refunit_B: 
            hx.set_reference_unit_B(refunit_B)
            if offset_B:
                hx.set_offset_B(offset_B)
            else:
                hx.tare_B()
                self.debug_msg("channel B offset: %s" % hx.OFFSET_B)

        return hx


    def init_co2(self, co2_conf):
        co2 = self.init_hx711(co2_conf)
        try:
            co2.set_reference_unit_A(co2_conf['refunit'])
        except KeyError:
            pass
        try:
            co2.set_offset_A(co2_conf['offset'])
        except KeyError:
            pass
        return co2

    
    def hx711_read_chA(self, hx):
        return int(hx.get_weight_A(3))

    
    def hx711_read_chB(self, hx):
        return int(hx.get_weight_B(3))


    def hx711_cal_chA(self, hx, real_w):
        ref = hx.REFERENCE_UNIT_A
        hx.set_reference_unit_A(1)
        raw_w = hx.get_weight_A(3)
        hx.set_reference_unit_A(ref)
        return raw_w / float(real_w)


    def hx711_cal_chB(self, hx, real_w):
        ref = hx.REFERENCE_UNIT_B
        hx.set_reference_unit_B(1)
        raw_w = hx.get_weight_B(3)
        hx.set_reference_unit_B(ref)
        return raw_w / float(real_w)

    
    def load_config(self, config_file="config.json"):
        try: 
            save = open(config_file, "r")
            config = json.load(save)
            save.close()
        except IOError:
            print "No config found at %s, using defaults" % config_file
            config = self.build_config()
	except ValueError:
            print "Config at %s has syntax issues, cannot load" % config_file
            config = None
        return config

    
    def save_config(self, config, config_file="config.json"):
        try:
            save = open(config_file, "w")
            json.dump(config, save, indent=2)
            save.close()
        except IOError as e:
            print "Could not save config: %s" % e.strerror

    
    def build_config(self):
        config = dict()
        config['co2'] = dict()
        config['co2']['size'] = [2.27, 1.8]
        config['co2']['dout'] = 12
        config['co2']['pd_sck'] = 13
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
        return config

    
    def text_header(self, y, message, fill="white"):
        W = self.device.width
        w, h = self.draw.textsize(message)
        self.draw.text(((W-w)/2, y), message, fill=fill)

    
    def text_align_center(self, x, y, message, fill="white"):
        w, h = self.draw.textsize(message)
        self.draw.text((x-(w/2), y), message, fill=fill)

    
    def fill_bar(self, x, y, min_w, max_w, w, outline="white", fill="red"):
        net_w = max(w - min_w, 0)
        max_net_w = max_w - min_w
        fill_percent = float(net_w) / float(max_net_w)
        max_y = self.device.height - 21
        min_y = y+1
        max_bar = max_y - min_y
        fill_height = min_y + (max_bar - (max_bar * fill_percent))
        self.draw.rectangle([x,y, x+20,self.device.height-20], outline=outline, fill="black")
        self.draw.rectangle([x+1,fill_height, x+19,max_y], outline=fill, fill=fill)

    
    def as_kg(self, val):
        return "%s kg" % "{0:.2f}".format(val / 1000.0)


    def read_weight(self, hx):
        hx.power_up()
        kegA = self.hx711_read_chA(hx)
        kegB = self.hx711_read_chB(hx)
        hx.power_down()
        return ( kegA, kegB )


    def render_st7735(self, weight, hx_conf):
        try:
            kegA = weight[0]
            kegA_name = hx_conf['channels']['A']['name'][0:13]
            kegA_min = hx_conf['channels']['A']['size'][1] * 1000
            kegA_max = kegA_min + ( hx_conf['channels']['A']['size'][0] * 1000 )
        except (ValueError, KeyError):
            # no channel A data
            kegA = 0
            kegA_name = None
            kegA_min = 0
            kegA_max = 0

        try:
            kegB = weight[1]
            kegB_name = hx_conf['channels']['B']['name'][0:13]
            kegB_min = hx_conf['channels']['B']['size'][1] * 1000
            kegB_max = kegB_min + ( hx_conf['channels']['B']['size'][0] * 1000 )
        except (ValueError, KeyError):
            # no channel B data
            kegB = 0
            kegB_name = None
            kegB_min = 0
            kegB_max = 0


        with canvas(self.device) as self.draw:
            self.debug_msg("%s: %s/%s  %s: %s/%s" % ( kegA_name, kegA, kegA_max, 
                                             kegB_name, kegB, kegB_max ))
            self.debug_msg("min: %s %s" % ( kegA_min, kegB_min ))
            self.debug_msg(self.as_degF(self.temp))
            self.debug_msg("CO2: "+str(self.get_co2_pct())+"%")

            self.text_header(0, "HOPLITE", fill="red")
            self.text_align_center(30, 0, self.as_degF(self.temp), fill="blue")
            self.text_align_center(130, 0, "CO2:"+str(self.get_co2_pct())+"%", fill="blue")

            if kegA_name:
                self.text_align_center(40, 15, kegA_name)
                self.fill_bar(30, 35, kegA_min, kegA_max, kegA)
                self.text_align_center(40, self.device.height-10, self.as_kg(kegA))

            if kegB_name:
                self.text_align_center(120, 15, kegB_name)
                self.fill_bar(110, 35, kegB_min, kegB_max, kegB)
                self.text_align_center(120, self.device.height-10, self.as_kg(kegB))


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


    def get_co2_pct(self):
        co2_max = self.config['co2']['size'][0] * 1000
        co2_tare = self.config['co2']['size'][1] * 1000
        co2_net_wt = max((self.co2_w - co2_tare), 0)
        co2_pct = co2_net_wt / float(co2_max)
        return int(co2_pct * 100)


    def as_degC(self, temp):
        return u'%s\u00b0C' % '{0:.1f}'.format(temp / 1000.0)


    def as_degF(self, temp):
        real_c = temp / 1000.0
        deg_f = real_c * (9.0/5.0) + 32.0
        return u'%s\u00b0F' % '{0:.1f}'.format(deg_f)


    def cleanup(self, signum=None, frame=None):
        self.save_config(self.config, self.config_file)
        for hx in self.hx_handles:
            try:
                hx.power_down()
            except RuntimeError:
                # GPIO already cleaned up
                pass
        GPIO.cleanup()
        try:
            self.ShMem.close()
            posix_ipc.unlink_shared_memory('/hoplite')
            self.ShLock.release()
            self.ShLock.unlink()
        except posix_ipc.ExistentialError:
            # shmem already cleaned up
            pass


    def setup_all_kegs(self):
        self.hx_handles = list()

        # grab each keg definition from the config
        for index, hx_conf in enumerate(self.config['hx']):
            hx = self.init_hx711(hx_conf)
            self.hx_handles.insert(index, hx)


    def main(self, config_file='config.json'):
        self.config_file = config_file
        self.config = self.load_config(self.config_file)
	if self.config == None:
            print "No valid config, bailing out"
            sys.exit()

        self.ShData = dict()
        self.ShData['data'] = dict()
        self.ShData['data']['weight'] = list()
        self.ShData['config'] = self.config
        self.shmem_write()

        self.device = self.init_st7735()
        self.co2 = self.init_co2(self.config['co2'])
        self.setup_all_kegs()
        
        index = 0

        while True:
            try:
                hx = self.hx_handles[index]

                weight = self.read_weight(hx)
                self.co2_w = self.hx711_read_chA(self.co2)
                self.temp = self.read_temp()

                self.render_st7735(weight, self.config['hx'][index])

                self.shmem_read()
                if self.ShData['config']:
                    self.config = self.ShData['config']
                try:
                    self.ShData['data']['weight'][index] = weight
                except IndexError:
                    self.ShData['data']['weight'].insert(index, weight)
                self.ShData['data']['temp'] = self.temp
                self.ShData['data']['co2'] = self.get_co2_pct()
                self.shmem_write()

                index += 1
                if index >= len(self.hx_handles):
                    index = 0

                time.sleep(3)
            except (KeyboardInterrupt, SystemExit, RuntimeError):
                self.cleanup()
                sys.exit()


# this is here in case we get run as a standalone script
if __name__ == '__main__':
    h = Hoplite()
    h.main()
