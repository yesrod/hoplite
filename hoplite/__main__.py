from . import Hoplite

import argparse
import sys
import RPi.GPIO as GPIO

def calibrate(channel, weight, conf_file):
    h = Hoplite()
    config = h.load_config(conf_file)
    if channel == "co2":
        print "CO2"
        print channel
        print weight
    elif channel == "kegA" or channel == "kegB":
        hx = h.init_hx711(config['hx'][0])
        if channel == "kegA":
            cal = h.hx711_cal_chA(hx, weight)
            ch = 'A'
        else:
            cal = h.hx711_cal_chB(hx, weight)
            ch = 'B'
        print "Calibration unit %s, saving to config" % cal
        config['hx'][0]['channels'][ch]['refunit'] = cal
        h.save_config(config, conf_file)
        GPIO.cleanup()
    else:
        print "Channel %s not found" % channel


def __main__():
    parser = argparse.ArgumentParser(description="HOPLITE: A kegerator monitoring script for RasPi")
    parser.add_argument('--config', 
                    type=str, 
                    help='Config file location.  Default: ./config.json')
    parser.add_argument('--cal', 
                    type=str, 
                    nargs=2, 
                    metavar=('CHAN', 'W'),
                    help='Calibrate a weight sensor using a test weight in grams.  Usage: --cal <kegA|kegB|co2> <test_weight>')

    parsed_args = parser.parse_args()

    if parsed_args.config:
        config = parsed_args.config
    else:
        config = "config.json"

    if parsed_args.cal:
        calibrate(parsed_args.cal[0], parsed_args.cal[1], config)
    else:
        h = Hoplite()
        h.main( config_file = config )

if __name__ == "__main__":
    __main__()

