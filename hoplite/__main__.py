from . import Hoplite

import argparse
import sys
import RPi.GPIO as GPIO

def calibrate(conf_file, index, channel, weight):
    h = Hoplite()
    config = h.load_config(conf_file)
    if index == "co2":
        co2 = h.init_co2(config['co2'])
        cal = h.hx711_cal_chA(co2, weight)

        config['co2']['refunit'] = cal
        print("Calibration unit %s, saved to config" % cal)
        h.save_config(config, conf_file)

        GPIO.cleanup()
        sys.exit()
    else:
        try:
            i = int(index) - 1
            hx = h.init_hx711(config['hx'][i])
        except (KeyError, ValueError):
            print("Sensor %s not found!" % index)
            sys.exit()

        if channel == 'A':
            cal = h.hx711_cal_chA(hx, weight)
            ch = 'A'
        elif channel == 'B':
            cal = h.hx711_cal_chB(hx, weight)
            ch = 'B'
        else:
            print("Sensor %s channel %s not found!" % (index, channel))
            GPIO.cleanup()
            sys.exit()
        try:
            config['hx'][i]['channels'][ch]['refunit'] = cal
            print("Calibration unit %s, saved to config" % cal)
        except KeyError:
            print("Sensor %s channel %s not found!" % (index, channel))
        h.save_config(config, conf_file)
        GPIO.cleanup()
        sys.exit()


def tare(conf_file, index=None, channel=None):
    h = Hoplite()
    config = h.load_config(conf_file)

    # co2 special case
    if index == 'co2':
        co2 = h.init_co2(config['co2'])
        co2.tare_A()
        try:
            config['co2']['offset'] = co2.OFFSET
            print("CO2 channel A offset saved as %s" % co2.OFFSET)
        except KeyError:
            pass

    # one sensor, one channel
    elif index != None and channel != None:
        try:
            i = int(index) - 1
            hx_conf = config['hx'][i]
            hx = h.init_hx711(hx_conf)
        except (KeyError, IndexError):
            print("Sensor %s not found!" % ( index ))
            sys.exit()

        if channel == 'A':
            hx.tare_A()
            try:
                hx_conf['channels']['A']['offset'] = hx.OFFSET
                print("Sensor %s channel A offset saved as %s" % (index, hx.OFFSET))
            except KeyError:
                 print("Sensor %s channel %s not found!" % ( index, channel ))

        elif channel == 'B':
            hx.tare_B()
            try:
                hx_conf['channels']['B']['offset'] = hx.OFFSET_B
                print("Sensor %s channel B offset saved as %s" % (index, hx.OFFSET_B))
            except KeyError:
                 print("Sensor %s channel %s not found!" % ( index, channel ))

        else:
            print("Sensor %s channel %s not found!" % ( index, channel ))


    # one sensor, all channels
    elif index != None and channel == None:
        try:
            i = int(index) - 1
            hx_conf = config['hx'][i]
            hx = h.init_hx711(hx_conf)
        except (KeyError, IndexError):
            print("Sensor %s not found!" % ( index ))
            sys.exit()

        hx.tare_A()
        try:
            hx_conf['channels']['A']['offset'] = hx.OFFSET
            print("Sensor %s channel A offset saved as %s" % (index, hx.OFFSET))
        except KeyError:
            pass

        hx.tare_B()
        try:
            hx_conf['channels']['B']['offset'] = hx.OFFSET_B
            print("Sensor %s channel B offset saved as %s" % (index, hx.OFFSET_B))
        except KeyError:
            pass

    # all sensors, all channels
    else:
        for index, hx_conf in enumerate(config['hx']):
            hx = h.init_hx711(hx_conf)
            hx.tare_A()
            try:
                hx_conf['channels']['A']['offset'] = hx.OFFSET
                print("Sensor %s channel A offset saved as %s" % (str(index + 1), hx.OFFSET))
            except KeyError:
                pass

            hx.tare_B()
            try:
                hx_conf['channels']['B']['offset'] = hx.OFFSET_B
                print("Sensor %s channel B offset saved as %s" % (str(index + 1), hx.OFFSET_B))
            except KeyError:
                pass

        co2 = h.init_co2(config['co2'])
        co2.tare_A()
        try:
            config['co2']['offset'] = co2.OFFSET
            print("CO2 channel A offset saved as %s" % co2.OFFSET)
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
                    type=str,
                    nargs='*',
                    metavar=('INDEX', 'CHAN'),
                    help='Tare all sensors. If run without any parameters, tares all sensors configured; otherwise tares the specific channel or sensor given. Make sure the sensor platforms are empty and sitting level before you run this! Usage: --tare [N|co2] [channel]')
    parser.add_argument('--debug',
                    action='store_true',
                    help='Enable debugging messages')

    parsed_args = parser.parse_args()

    if parsed_args.config:
        config = parsed_args.config
    else:
        config = "config.json"

    if hasattr(parsed_args, 'tare'):
        if len(parsed_args.tare) == 0:
            tare(config)
        elif len(parsed_args.tare) == 1:
            tare(config, index=parsed_args.tare[0])
        elif len(parsed_args.tare) == 2:
            tare(config, index=parsed_args.tare[0], channel=parsed_args.tare[1])
        else:
            raise argparse.ArgumentTypeError('--tare takes up to two arguments')
            sys.exit()
    elif parsed_args.cal:
        calibrate(config, parsed_args.cal[0], parsed_args.cal[1], parsed_args.cal[2])
    else:
        h = Hoplite()
        if parsed_args.debug:
            h.debug = True
        h.main( config_file = config )

if __name__ == "__main__":
    __main__()

