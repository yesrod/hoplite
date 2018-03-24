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

    # hx711_1, for keg weighting, and its values
    global kegs
    global kegA
    global kegB

    # temperature sensor output
    global temp

    # shared memory segment for communicating with web interface,
    # semaphore lock, and data to be shared
    global ShMem
    global ShLock
    global ShData

    # config file location
    global config_file

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

        mem = posix_ipc.SharedMemory('/hoplite', flags=posix_ipc.O_CREAT, size=1024)
        self.ShMem = mmap.mmap(mem.fd, mem.size)
        mem.close_fd()

        self.ShLock = posix_ipc.Semaphore('/hoplite', flags=posix_ipc.O_CREAT)
        self.ShLock.release()


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

    
    def init_hx711(self):
        dout = self.config['kegs']['dout']
        pd_sck = self.config['kegs']['pd_sck']
        offset_A = self.config['kegs']['kegA']['offset']
        refunit_A = self.config['kegs']['kegA']['refunit']
        offset_B = self.config['kegs']['kegB']['offset']
        refunit_B = self.config['kegs']['kegB']['refunit']
        hx = HX711(dout, pd_sck)
        hx.set_reading_format("LSB", "MSB")
        hx.set_reference_unit_A(refunit_A)
        hx.set_reference_unit_B(refunit_B)
        hx.reset()
        if offset_A:
            hx.set_offset_A(offset_A)
        else:
            hx.tare_A()
            self.config['kegs']['kegA']['offset'] = hx.OFFSET_A
        if offset_B:
            hx.set_offset_B(offset_B)
        else:
            hx.tare_B()
            self.config['kegs']['kegB']['offset'] = hx.OFFSET_B
        return hx

    
    def hx711_read_chA(self, hx):
        return int(hx.get_weight_A(3))

    
    def hx711_read_chB(self, hx):
        return int(hx.get_weight_B(3))

    
    def load_config(self, config_file="config.json"):
        try: 
            save = open(config_file, "r")
            self.config = json.load(save)
            save.close()
        except (IOError, ValueError):
            print "no config found, using defaults"
            self.config = self.build_config()
        return self.config

    
    def save_config(self, config, config_file="config.json"):
        try:
            save = open(config_file, "w")
            json.dump(self.config, save, indent=2)
            save.close()
        except IOError as e:
            print "Could not save config: %s" % e.strerror

    
    def build_config(self):
        config = dict()
        config['kegs'] = dict()
        config['kegs']['kegA'] = dict()
        config['kegs']['kegB'] = dict()
        config['kegs']['kegA']['offset'] = None
        config['kegs']['kegA']['refunit'] = 21.7
        config['kegs']['kegA']['name'] = "Yuengling"
        config['kegs']['kegA']['size'] = self.keg_data['half_bbl']
        config['kegs']['kegA']['size_name'] = 'half_bbl'
        config['kegs']['kegB']['offset'] = None
        config['kegs']['kegB']['refunit'] = 5.4
        config['kegs']['kegB']['name'] = "Angry Orchard"
        config['kegs']['kegB']['size'] = self.keg_data['sixth_bbl']
        config['kegs']['kegB']['size_name'] = 'sixth_bbl'
        config['kegs']['dout'] = 5
        config['kegs']['pd_sck'] = 6
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


    def read_weight(self):
        self.kegs.power_up()
        self.kegA = self.hx711_read_chA(self.kegs)
        self.kegB = self.hx711_read_chB(self.kegs)
        self.kegs.power_down()


    def render_st7735(self):
        kegA_name = self.config['kegs']['kegA']['name']
        kegB_name = self.config['kegs']['kegB']['name']
        kegA_min = self.config['kegs']['kegA']['size'][1] * 1000
        kegB_min = self.config['kegs']['kegB']['size'][1] * 1000
        kegA_max = kegA_min + ( self.config['kegs']['kegA']['size'][0] * 1000 )
        kegB_max = kegB_min + ( self.config['kegs']['kegB']['size'][0] * 1000 )

        with canvas(self.device) as self.draw:
            print "%s: %s/%s  %s: %s/%s" % ( kegA_name, self.kegA, kegA_max, 
                                             kegB_name, self.kegB, kegB_max )
            print "min: %s %s" % ( kegA_min, kegB_min )

            self.text_header(0, "HOPLITE", fill="red")
            self.draw.text((0,0), self.as_degC(self.temp), fill="blue")

            self.text_align_center(40, 10, kegA_name)
            self.fill_bar(30, 20, kegA_min, kegA_max, self.kegA)
            self.text_align_center(40, self.device.height-10, self.as_kg(self.kegA))

            self.text_align_center(120, 10, kegB_name)
            self.fill_bar(110, 20, kegB_min, kegB_max, self.kegB)
            self.text_align_center(120, self.device.height-10, self.as_kg(self.kegB))


    def read_temp(self):
        #/sys/bus/w1/devices/28-0517a036c6ff/hwmon/hwmon0/temp1_input
        base_dir = '/sys/bus/w1/devices/'
        device_folder = glob.glob(base_dir + '28*')[0]
        device_file = device_folder + '/hwmon/hwmon0/temp1_input'
        f = open(device_file, 'r')
        temp = f.read()
        f.close()
        self.temp = int(temp)


    def as_degC(self, temp):
        return u"%s\u00b0C" % "{0:.1f}".format(temp / 1000.0)


    def cleanup(self):
        self.save_config(self.config, self.config_file)
        self.kegs.power_down()
        GPIO.cleanup()
        self.ShMem.close()
        posix_ipc.unlink_shared_memory('/hoplite')
        self.ShLock.release()
        self.ShLock.unlink()


    def main(self, config_file='config.json'):
        self.config_file = config_file
        self.config = self.load_config(self.config_file)

        self.ShData = dict()
        self.ShData['data'] = dict()
        self.ShData['config'] = self.config

        self.shmem_write()

        self.device = self.init_st7735()

        self.kegs = self.init_hx711()
        self.kegs.power_down()
        
        while True:
            try:
                self.read_weight()
                self.read_temp()
                self.render_st7735()
                self.shmem_read()
                if self.ShData['config']:
                    self.config = self.ShData['config']
                self.ShData['data']['kegA_w'] = self.kegA
                self.ShData['data']['kegB_w'] = self.kegB
                self.shmem_write()
                time.sleep(5)
            except (KeyboardInterrupt, SystemExit):
                self.cleanup()
                sys.exit()


# this is here in case we get run as a standalone script
if __name__ == '__main__':
    h = Hoplite()
    h.main()
