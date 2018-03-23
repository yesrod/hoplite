from . import Hoplite

import argparse
import sys
#print sys.argv

parser = argparse.ArgumentParser(description="HOPLITE: A kegerator monitoring script for RasPi")
parser.add_argument('--config', type=str, help='Config file location.  Default: ./config.json')

parsed_args = parser.parse_args()

h = Hoplite()
h.main( config_file = parsed_args.config )

