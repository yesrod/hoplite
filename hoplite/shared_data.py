
from .config import Config
from .sensor import Sensor


class SharedData():

    def __init__(self, config=None):
        if config:
            self.config = config
        else:
            self.config = Config()

        self.kegs = []

        self.sensors = []

    def get_sensor(self, port):
        """
        Get a specific Sensor() instance, by port

        Returns: Sensor() instance, or None if instance is not found
        """

        s = [ x for x in self.sensors if x.get_port() == port ]
        if len(s) > 1:
            raise ValueError("found %s instances of Sensor() with port %s, this should never happen" % (len(s), port))
        elif len(s) == 1:
            return s[0]
        else:
            return None


    def add_sensor(
        self,
        port,
        offset_A = None,
        refunit_A = None,
        offset_B = None,
        refunit_B = None
    ):
        """Create a new sensor and add to the __sensors__ dict"""
        if not self.get_sensor(port):
            self.sensors.append(
                Sensor(
                    port, 
                    offset_A,
                    refunit_A,
                    offset_B,
                    refunit_B
                )
            )
        else:
            raise ValueError("Sensor at port %s already defined" % port)
        