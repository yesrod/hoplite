HOPLITE
-------

[Wiki](https://github.com/yesrod/hoplite/wiki)

[Configuration](https://github.com/yesrod/hoplite/wiki/Configuration)

[Screenshots](https://github.com/yesrod/hoplite/wiki/Screenshots)

A Python module to monitor the status of my kegerator.  Runs on a Raspberry Pi
that has several HX711 load cell amplifiers and an ST7735 LCD attached.

Hardware docs will be forthcoming when the hardware is done.

Supports:
 * Reporting beer levels via weight, using HX711 load cell amplifiers
 * Temperature monitoring
 * Outputting data to an attached ST7735 LCD
 * A web interface that reports data and allows configuring keg names and 
   sizes in a more convenient manner

INSTALLATION
------------

For now you'll need to use my version of hx711py.  Install that first.

```
sudo pip install git+https://github.com/yesrod/hx711py.git
```

Clone this respository and run
```
sudo python setup.py install
```

Or use pip:
```
sudo pip install git+https://github.com/yesrod/hoplite.git
```

CONFIGURATION
-------------
Use the provided example config, or create a default config by specifying 
a path to a config that doesn't exist yet:
```
python -m hoplite --config ./new-config.json
```

The config is in JSON.  I've tried to make it as self-documenting as possible.
More documentation on configuration will be provided eventually.

After you have a roughly accurate config, tare all the connected HX711s:
```
python -m hoplite --tare --config /path/to/config.json
```

Then get a known weight of some sort (in grams) and calibrate your weight 
sensors:
```
python -m hoplite --cal 1 A 1000
# repeat for all channels defined in the config
```

RUNNING HOPLITE
---------------

For the main daemon (start this before the web interface)
```
python -m hoplite
```

Optionally, specify a config file location
```
python -m hoplite --config /etc/hoplite.conf
```

For the web interface
```
python -m hoplite.web
```

Systemd service definitions will be added eventually.

TODO:
-----
 * Better setup docs
 * Hardware schematics and notes
 * More configurables via the web interface
   * Percentage/weight/pints left estimate display configurability
   * Preferred display units (will always use metric internally though)
 * Temperature and beer level history graphing
 * Systemd service definitions
