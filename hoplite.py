from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.lcd.device import st7735
from luma.lcd.aux import backlight
import RPi.GPIO as GPIO
import sys
import time
import json

sys.path.append('./hx711py/')
from hx711 import HX711

# keg data dictionary
# value is list( volume in liters, empty weight in kg )
keg_data = {
    'half_bbl': (58.6, 13.6),
    'tall_qtr_bbl': (29.3, 10),
    'short_qtr_bbl': (29.3, 10),
    'sixth_bbl': (19.5, 7.5),
    'corny': (18.9, 4),
}

def init_st7735():
    light = backlight(gpio=GPIO, gpio_LIGHT=18, active_low=False)
    light.enable(True)
    serial = spi(port=0, device=0, gpio_DC=23, gpio_RST=24)
    device = st7735(serial)
    return device

def init_hx711(config):
    dout = config['hx711_1']['dout']
    pd_sck = config['hx711_1']['pd_sck']
    offset_A = config['hx711_1']['chA']['offset']
    refunit_A = config['hx711_1']['chA']['refunit']
    offset_B = config['hx711_1']['chB']['offset']
    refunit_B = config['hx711_1']['chB']['refunit']
    hx = HX711(dout, pd_sck)
    hx.set_reading_format("LSB", "MSB")
    hx.set_reference_unit_A(refunit_A)
    hx.set_reference_unit_B(refunit_B)
    hx.reset()
    if offset_A:
        hx.set_offset_A(offset_A)
    else:
        hx.tare_A()
        config['hx711_1']['chA']['offset'] = hx.OFFSET_A
    if offset_B:
        hx.set_offset_B(offset_B)
    else:
        hx.tare_B()
        config['hx711_1']['chB']['offset'] = hx.OFFSET_B
    return hx

def hx711_read_chA(hx):
    return int(hx.get_weight_A(5))

def hx711_read_chB(hx):
    return int(hx.get_weight_B(5))

def load_config():
    try: 
        save = open("config.json", "r")
        config = json.load(save)
        save.close()
    except (IOError, ValueError):
        print "no config found, using defaults"
        config = build_config()
    return config

def save_config(config):
    try:
        save = open("config.json", "w")
        json.dump(config, save, indent=2)
        save.close()
    except IOError:
        print "Could not save config: %s" % e.strerror

def build_config():
    config = dict()
    config['hx711_1'] = dict()
    config['hx711_1']['chA'] = dict()
    config['hx711_1']['chB'] = dict()
    config['hx711_1']['chA']['offset'] = None
    config['hx711_1']['chA']['refunit'] = 21.7
    config['hx711_1']['chA']['keg_name'] = "Yuengling"
    config['hx711_1']['chA']['keg_size'] = keg_data['half_bbl']
    config['hx711_1']['chB']['offset'] = None
    config['hx711_1']['chB']['refunit'] = 5.4
    config['hx711_1']['chB']['keg_name'] = "Angry Orchard"
    config['hx711_1']['chB']['keg_size'] = keg_data['sixth_bbl']
    config['hx711_1']['dout'] = 5
    config['hx711_1']['pd_sck'] = 6
    return config

def text_header(device, draw, y, message, fill="white"):
    W = device.width
    w, h = draw.textsize(message)
    draw.text(((W-w)/2, y), message, fill=fill)

def text_align_center(device, draw, x, y, message, fill="white"):
    w, h = draw.textsize(message)
    draw.text(((x-w)/2, y), message, fill=fill)

def fill_bar(device, draw, x, y, min_w, max_w, w, outline="white", fill="red"):
    trim_w = max(min_w, min(w, max_w))
    fill_percent = float(trim_w) / float(max_w)
    max_y = device.height - 21
    min_y = y+1
    max_bar = max_y - min_y
    fill_height = min_y + (max_bar - (max_bar * fill_percent))
    draw.rectangle([x,y, x+20,device.height-20], outline=outline, fill="black")
    draw.rectangle([x+1,fill_height, x+19,max_y], outline=fill, fill=fill)

def as_kg(val):
    return "%s kg" % str(val / 1000.0)

print keg_data

config = load_config()

print config

device = init_st7735()
hx = init_hx711(config)

hx.power_down()

chA_name = config['hx711_1']['chA']['keg_name']
chB_name = config['hx711_1']['chB']['keg_name']
chA_min = config['hx711_1']['chA']['keg_size'][1] * 1000
chB_min = config['hx711_1']['chB']['keg_size'][1] * 1000
chA_max = chA_min + ( config['hx711_1']['chA']['keg_size'][0] * 1000 )
chB_max = chB_min + ( config['hx711_1']['chB']['keg_size'][0] * 1000 ) 

while True:
    try:
        hx.power_up()

        chA = hx711_read_chA(hx)
        chB = hx711_read_chB(hx)
        print "%s: %s/%s  %s: %s/%s" % ( chA_name, as_kg(chA), as_kg(chA_max), chB_name, as_kg(chB), as_kg(chB_max) )
        print "min: %s %s" % ( chA_min, chB_min )

        with canvas(device) as draw:
            text_header(device, draw, 0, "HOPLITE", fill="red")

            text_align_center(device, draw, 30, 10, chA_name)
            fill_bar(device, draw, 30, 20, chA_min, chA_max, chA)
            draw.text((30, device.height-10), as_kg(chA), fill="white")

            text_align_center(device, draw, 30, 10, chB_name)
            fill_bar(device, draw, 110, 20, chB_min, chB_max, chB)
            draw.text((100, device.height-10), as_kg(chB), fill="white")

        hx.power_down()
        time.sleep(5)
    except (KeyboardInterrupt, SystemExit):
        save_config(config)
        hx.power_down()
        GPIO.cleanup()
        sys.exit()

