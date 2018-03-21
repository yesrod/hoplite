from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.lcd.device import st7735
from luma.lcd.aux import backlight
import RPi.GPIO as GPIO
import sys
import time
import json
from hx711 import HX711


class hoplite():
    # keg data dictionary
    # value is list( volume in liters, empty weight in kg )
    global keg_data
    keg_data = {
        'half_bbl': (58.6, 13.6),
        'tall_qtr_bbl': (29.3, 10),
        'short_qtr_bbl': (29.3, 10),
        'sixth_bbl': (19.5, 7.5),
        'corny': (18.9, 4),
    }
    
    # config
    global config

    # output device and draw handle
    global device
    global draw

    # hx711_1, for keg weighting
    global hx
    global chA
    global chB

    def __init__(self):
        self.config = self.load_config()

        self.device = self.init_st7735()

        self.hx = self.init_hx711()
        self.hx.power_down()


    def init_st7735(self):
        light = backlight(gpio=GPIO, gpio_LIGHT=18, active_low=False)
        light.enable(True)
        serial = spi(port=0, device=0, gpio_DC=23, gpio_RST=24)
        device = st7735(serial)
        return device

    
    def init_hx711(self):
        dout = self.config['hx711_1']['dout']
        pd_sck = self.config['hx711_1']['pd_sck']
        offset_A = self.config['hx711_1']['chA']['offset']
        refunit_A = self.config['hx711_1']['chA']['refunit']
        offset_B = self.config['hx711_1']['chB']['offset']
        refunit_B = self.config['hx711_1']['chB']['refunit']
        hx = HX711(dout, pd_sck)
        hx.set_reading_format("LSB", "MSB")
        hx.set_reference_unit_A(refunit_A)
        hx.set_reference_unit_B(refunit_B)
        hx.reset()
        if offset_A:
            hx.set_offset_A(offset_A)
        else:
            hx.tare_A()
            self.config['hx711_1']['chA']['offset'] = hx.OFFSET_A
        if offset_B:
            hx.set_offset_B(offset_B)
        else:
            hx.tare_B()
            self.config['hx711_1']['chB']['offset'] = hx.OFFSET_B
        return hx

    
    def hx711_read_chA(self, hx):
        return int(hx.get_weight_A(5))

    
    def hx711_read_chB(self, hx):
        return int(hx.get_weight_B(5))

    
    def load_config(self):
        try: 
            save = open("config.json", "r")
            self.config = json.load(save)
            save.close()
        except (IOError, ValueError):
            print "no config found, using defaults"
            self.config = self.build_config()
        return self.config

    
    def save_config(self, config):
        try:
            save = open("config.json", "w")
            json.dump(self.config, save, indent=2)
            save.close()
        except IOError:
            print "Could not save config: %s" % e.strerror

    
    def build_config(self):
        self.config = dict()
        self.config['hx711_1'] = dict()
        self.config['hx711_1']['chA'] = dict()
        self.config['hx711_1']['chB'] = dict()
        self.config['hx711_1']['chA']['offset'] = None
        self.config['hx711_1']['chA']['refunit'] = 21.7
        self.config['hx711_1']['chA']['keg_name'] = "Yuengling"
        self.config['hx711_1']['chA']['keg_size'] = keg_data['half_bbl']
        self.config['hx711_1']['chB']['offset'] = None
        self.config['hx711_1']['chB']['refunit'] = 5.4
        self.config['hx711_1']['chB']['keg_name'] = "Angry Orchard"
        self.config['hx711_1']['chB']['keg_size'] = keg_data['sixth_bbl']
        self.config['hx711_1']['dout'] = 5
        self.config['hx711_1']['pd_sck'] = 6
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
        self.hx.power_up()
        self.chA = self.hx711_read_chA(self.hx)
        self.chB = self.hx711_read_chB(self.hx)
        self.hx.power_down()


    def render_st7735(self):
        chA_name = self.config['hx711_1']['chA']['keg_name']
        chB_name = self.config['hx711_1']['chB']['keg_name']
        chA_min = self.config['hx711_1']['chA']['keg_size'][1] * 1000
        chB_min = self.config['hx711_1']['chB']['keg_size'][1] * 1000
        chA_max = chA_min + ( self.config['hx711_1']['chA']['keg_size'][0] * 1000 )
        chB_max = chB_min + ( self.config['hx711_1']['chB']['keg_size'][0] * 1000 )

        print "%s: %s/%s  %s: %s/%s" % ( chA_name, self.chA, chA_max, 
                                         chB_name, self.chB, chB_max )
        print "min: %s %s" % ( chA_min, chB_min )

        self.text_header(0, "HOPLITE", fill="red")

        self.text_align_center(40, 10, chA_name)
        self.fill_bar(30, 20, chA_min, chA_max, self.chA)
        self.text_align_center(40, self.device.height-10, self.as_kg(self.chA))

        self.text_align_center(120, 10, chB_name)
        self.fill_bar(110, 20, chB_min, chB_max, self.chB)
        self.text_align_center(120, self.device.height-10, self.as_kg(self.chB))


    def main(self):
        
        while True:
            try:
                self.read_weight()

                with canvas(self.device) as self.draw:
                    self.render_st7735()
        
                time.sleep(5)
            except (KeyboardInterrupt, SystemExit):
                self.save_config(self.config)
                self.hx.power_down()
                GPIO.cleanup()
                sys.exit()


# this is here in case we get run as a standalone script
if __name__ == '__main__':
    h = hoplite()
    h.main()
