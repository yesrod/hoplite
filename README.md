HOPLITE
-------

[Screenshots](https://github.com/yesrod/hoplite/wiki/Screenshots)

[Hardware](https://github.com/yesrod/hoplite/wiki/Hardware)

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

You'll save time and skip having to install ```gfortran``` if you install the repo version of ```python-numpy```.
```
sudo apt-get update
sudo apt-get install python-numpy
```

I also recommend disabling CPU frequency scaling.  On my system, this fixed weight updates occasionally failing, causing keg weights to fluctuate randomly.
```
sudo apt-get install cpufrequtils
echo "GOVERNOR=performance" | sudo tee /etc/default/cpufrequtils
sudo systemctl restart cpufrequtils
```

For now you'll need to use my version of hx711py.  Install that first.
```
sudo pip install git+https://github.com/yesrod/hx711py.git
```

Finally, clone this respository and run
```
sudo python setup.py install
```

Or use pip:
```
sudo pip install git+https://github.com/yesrod/hoplite.git
```

HARDWARE
--------
See [Hardware](https://github.com/yesrod/hoplite/wiki/Hardware)

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
See [To-do list](https://github.com/yesrod/hoplite/wiki/Todo)
