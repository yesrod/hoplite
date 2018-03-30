from . import Hoplite

import argparse
import sys
import RPi.GPIO as GPIO

def calibrate(index, channel, weight, conf_file):
    h = Hoplite()
    config = h.load_config(conf_file)
    if index == "co2":
        co2 = h.init_co2(config['co2'])
        cal = h.hx711_cal_chA(co2, weight)

        config['co2']['refunit'] = cal
        print "Calibration unit %s, saved to config" % cal
        h.save_config(config, conf_file)

        GPIO.cleanup()
        sys.exit()
    else:
        try:
            i = int(index) - 1
            hx = h.init_hx711(config['hx'][i])
        except (KeyError, ValueError):
            print 'Sensor %s not found!' % index
            GPIO.cleanup()
            sys.exit()

        if channel == 'A':
            cal = h.hx711_cal_chA(hx, weight)
            ch = 'A'
        elif channel == 'B':
            cal = h.hx711_cal_chB(hx, weight)
            ch = 'B'
        else:
            print 'Sensor %s channel %s not found!' % (index, channel)
            GPIO.cleanup()
            sys.exit()
        try:
            config['hx'][i]['channels'][ch]['refunit'] = cal
            print "Calibration unit %s, saved to config" % cal
        except KeyError:
            print 'Sensor %s channel %s not found!' % (index, channel)
        h.save_config(config, conf_file)
        GPIO.cleanup()
        sys.exit()


def tare(conf_file):
    h = Hoplite()
    config = h.load_config(conf_file)

    for index, hx_conf in enumerate(config['hx']):
        hx = h.init_hx711(hx_conf)
        hx.tare_A()
        try:
            hx_conf['channels']['A']['offset'] = hx.OFFSET_A
            print "Sensor %s channel A offset saved as %s" % (str(index + 1), hx.OFFSET_A)
        except KeyError:
            pass

        hx.tare_B()
        try:
            hx_conf['channels']['B']['offset'] = hx.OFFSET_B
            print "Sensor %s channel B offset saved as %s" % (str(index + 1), hx.OFFSET_B)
        except KeyError:
            pass

    co2 = h.init_co2(config['co2'])
    co2.tare_A()
    try:
        config['co2']['offset'] = co2.OFFSET_A
        print "CO2 channel A offset saved as %s" % co2.OFFSET_A
    except KeyError:
        pass

    h.save_config(config, conf_file)
    GPIO.cleanup()
    sys.exit()


def __main__():
    parser = argparse.ArgumentParser(description="HOPLITE: A kegerator monitoring script for RasPi")
    parser.add_argument('--config', 
                    type=str, 
                    help='Config file location.  Default: ./config.json')
    parser.add_argument('--cal', 
                    type=str, 
                    nargs=3, 
                    metavar=('INDEX', 'CHAN', 'W'),
                    help='Calibrate a weight sensor using a test weight in grams. Weight sensor index is integer as defined in the config file: first sensor is 1, second is 2, etc. Special channel \'co2\' is for the CO2 sensor. Channel is either \'A\' or \'B\'. Usage: --cal <N|co2> <channel> <test_weight>')
    parser.add_argument('--tare',
                    action='store_true',
                    help='Tare all sensors.  Make sure the sensor platforms are empty and sitting level before you run this!')

    parsed_args = parser.parse_args()

    if parsed_args.config:
        config = parsed_args.config
    else:
        config = "config.json"

    if parsed_args.tare:
        tare(config)
    elif parsed_args.cal:
        calibrate(parsed_args.cal[0], parsed_args.cal[1], parsed_args.cal[2], config)
    else:
        h = Hoplite()
        h.main( config_file = config )

if __name__ == "__main__":
    __main__()

