from .hoplite import Hoplite

import argparse
import sys
import RPi.GPIO as GPIO
from hx711 import HX711

def calibrate(conf_file, index, channel, weight):
    h = Hoplite(debug=parsed_args.debug)
    config = h.load_config(config_file=conf_file)
    try:
        hx = h.init_hx711(config['hx'][int(index)])
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
        config['hx'][int(index)]['channels'][ch]['refunit'] = cal
        print("Calibration unit %s, saved to config" % cal)
    except KeyError:
        print("Sensor %s channel %s not found!" % (index, channel))
    h.save_config(config, conf_file)
    GPIO.cleanup()
    sys.exit()


def tare(conf_file, index=None, channel=None):
    h = Hoplite(debug=parsed_args.debug)
    config = h.load_config(conf_file)

    # one sensor, one or both channels
    if index != None:
        try:
            hx_conf = config['hx'][int(index)]
            dout = hx_conf['dout']
            pd_sck = hx_conf['pd_sck']
            h.debug_msg("dout, pd_sck: %s %s" % (dout, pd_sck))
            hx = HX711(dout, pd_sck)
            hx.set_reading_format("MSB", "MSB")
            hx.reset()
        except (KeyError, IndexError):
            print("Sensor at index %s not found!" % ( index ))
            sys.exit()

        if channel == 'A' or channel == None:
            hx.set_reference_unit_A(1)
            hx.tare_A()
            h.debug_msg("refunit, offset: %s %s" % hx.get_reference_unit_A(), hx.get_offset_A())
            try:
                hx_conf['channels']['A']['offset'] = hx.OFFSET
                print("Sensor %s channel A offset saved as %s" % (index, hx.OFFSET))
            except KeyError:
                print("Sensor %s channel %s not found!" % ( index, channel ))
        elif channel == 'B' or channel == None:
            hx.set_reference_unit_B(1)
            hx.tare_B()
            hx.debug_msg("refunit, offset: %s %s" % hx.get_reference_unit_B(), hx.get_offset_B())
            try:
                hx_conf['channels']['B']['offset'] = hx.OFFSET_B
                print("Sensor %s channel B offset saved as %s" % (index, hx.OFFSET_B))
            except KeyError:
                print("Sensor %s channel %s not found!" % ( index, channel ))
        else:
            print("Sensor %s channel %s not found!" % ( index, channel ))

    # all sensors, all channels
    else:
        for index, hx_conf in enumerate(config['hx']):
            dout = hx_conf['dout']
            pd_sck = hx_conf['pd_sck']
            hx = HX711(dout, pd_sck)
            h.debug_msg("dout, pd_sck: %s %s" % (dout, pd_sck))
            hx.set_reading_format("MSB", "MSB")
            hx.reset()

            hx.set_reference_unit_A(1)
            hx.tare_A()
            h.debug_msg("refunit, offset: %s %s" % hx.get_reference_unit_A(), hx.get_offset_A())
            try:
                hx_conf['channels']['A']['offset'] = hx.OFFSET
                print("Sensor %s channel A offset saved as %s" % (str(index), hx.OFFSET))
            except KeyError:
                pass

            hx.set_reference_unit_B(1)
            hx.tare_B()
            h.debug_msg("refunit, offset: %s %s" % hx.get_reference_unit_B(), hx.get_offset_B())
            try:
                hx_conf['channels']['B']['offset'] = hx.OFFSET_B
                print("Sensor %s channel B offset saved as %s" % (str(index), hx.OFFSET_B))
            except KeyError:
                pass

    h.save_config(config, conf_file)
    GPIO.cleanup()
    sys.exit()


def __main__():
    global parsed_args
    parser = argparse.ArgumentParser(description="HOPLITE: A kegerator monitoring script for RasPi")
    parser.add_argument('--config', 
                    type=str, 
                    help='Config file location.  Default: ./config.json')
    parser.add_argument('--api',
                    type=str,
                    help='Address where the API should listen.  Format is <ip>:<port>.  Port is optional.  Default is 0.0.0.0:5000 (listen on all IPs at port 5000)')
    parser.add_argument('--cal', 
                    type=str, 
                    nargs=3, 
                    metavar=('INDEX', 'CHAN', 'W'),
                    help='Calibrate a weight sensor using a test weight in grams. Weight sensor index is integer as defined in the config file: first sensor is 0, second is 1, etc. Channel is either \'A\' or \'B\'. Usage: --cal <N> <channel> <test_weight>')
    parser.add_argument('--tare',
                    type=str,
                    nargs='*',
                    metavar=('INDEX', 'CHAN'),
                    help='Tare all sensors. If run without any parameters, tares all sensors configured; otherwise tares the specific channel or sensor given. Make sure the sensor platforms are empty and sitting level before you run this! Usage: --tare [N] [channel]')
    parser.add_argument('--debug',
                    action='store_true',
                    help='Enable debugging messages')

    parsed_args = parser.parse_args()

    if parsed_args.config:
        config = parsed_args.config
    else:
        config = "config.json"

    if parsed_args.tare != None:
        if len(parsed_args.tare) == 0:
            tare(config)
        elif len(parsed_args.tare) == 1:
            tare(config, index=parsed_args.tare[0])
        elif len(parsed_args.tare) == 2:
            tare(config, index=parsed_args.tare[0], channel=parsed_args.tare[1])
        else:
            raise argparse.ArgumentTypeError('--tare takes up to two arguments')
    elif parsed_args.cal:
        calibrate(config, parsed_args.cal[0], parsed_args.cal[1], parsed_args.cal[2])
    else:
        h = Hoplite(debug=parsed_args.debug)
        h.main( config_file = config , api_listen = parsed_args.api )

if __name__ == "__main__":
    __main__()
