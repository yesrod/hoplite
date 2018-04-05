HOPLITE
-------

[Screenshots](https://github.com/yesrod/hoplite/wiki/Screenshots)

[Configuration](https://github.com/yesrod/hoplite/wiki/Configuration)

[Wiki](https://github.com/yesrod/hoplite/wiki)

A Python module to monitor the status of a kegerator.  Runs on a Raspberry Pi
that has one or more HX711 load cell amplifiers and an ST7735 LCD attached.

Hardware docs will be forthcoming when the hardware is done.

Supports:
 * Monitoring beer levels via weight, using HX711 load cell amplifiers
 * Monitoring CO2 tank levels, also via HX711s
 * Temperature monitoring via DS18B20 1-wire bus temp sensor
 * Outputting data to an attached ST7735 LCD
 * A web interface that reports data and allows configuring keg names and 
   sizes on-the-fly in a more convenient manner

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

HARDWARE
--------
The ST7735 LCD is connected as described in the 
[luma.lcd](http://luma-lcd.readthedocs.io/en/latest/install.html#st7735) docs.

The HX711s can be connected to any two free GPIO pins.  The ```pd_sck``` and 
```dout``` values in the config should then be updated to reference the GPIO
pin numbers (Broadcom-style logical numbers, not physical pin numbers) you 
chose.

The HX711s MUST be powered from the 3.3v bus of the RasPi, or another 3.3v 
source.  5v power will cause jittery unreliable readings in the short term, 
and damage to the Pi over time (the Pi GPIO is only rated for 3.3v).

The DS18B20 is a 1-wire bus sensor.  Some info on connecting that can be found
[here](https://thepihut.com/blogs/raspberry-pi-tutorials/18095732-sensors-temperature-with-the-1-wire-interface-and-the-ds18b20).

CONFIGURATION
-------------
Use the provided example config, or create a default config by specifying 
a path to a config that doesn't exist yet:
```
mkdir /etc/hoplite
python -m hoplite --config /etc/hoplite/config.json
```

The config is in JSON.  I've tried to make it as self-documenting as possible.
More documentation on configuration will be provided eventually.

After you have a roughly accurate config, tare all the connected HX711s:
```
python -m hoplite --tare --config /etc/hoplite/config.json
```

Then get a known weight of some sort (in grams) and calibrate your weight 
sensors:
```
python -m hoplite --cal 1 A 1000 --config /etc/hoplite/config.json
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
python -m hoplite --config /etc/hoplite/config.json
```

For the web interface
```
python -m hoplite.web
```
#### systemd
Systemd service files are in the ```systemd/``` folder in the repo.

These will run Hoplite as root - this isn't a requirement, however. Hoplite
will run as a non-root user, as long as the user is a member of the 
```gpio```, ```i2c``` and ```spi``` groups.

```
cp systemd/hoplite*.system /etc/systemd/system/
systemctl daemon-reload
systemctl start hoplite
systemctl start hoplite-web
```

To start on boot, install the files as above, then 
```
systemctl enable hoplite
systemctl enable hoplite-web
```

TODO:
-----
 * Better setup docs
 * Hardware schematics and notes
 * More configurables via the web interface
   * Percentage/weight/pints left estimate display configurability
   * Preferred display units (will always use metric internally though)
 * Temperature and beer level history graphing
