HOPLITE
-------

A Python module to monitor the status of my kegerator.  Runs on a Raspberry Pi.

Supports:
 * Reporting beer levels via weight
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

RUNNING HOPLITE
---------------

For the main daemon (start this before the web interface)
```
python -m hoplite
```

For the web interface
```
python -m hoplite.web
```

TODO:
-----
 * More configurables via the web interface
   * Percentage/weight/pints left estimate display configurability
   * Preferred display units (will always use metric internally though)
 * Temperature and beer level history graphing
 * Systemd service definitions
 * Make it not look like butt
