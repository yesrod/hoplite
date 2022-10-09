

from .sensor import Sensor

# TODO: I have no idea if this will work.
# Depending on how Python handles objects, if we get_sensor() to get a sensor instance,
# then update that sensor instance, those changes might not "stick" to the original
# instance.
#
# Be aware of this, and be ready to add update_sensor() or whatever if needed.


# A list containing all instantiated Sensor() instances
__sensors__ = []


def get_sensor(port):
    """
    Get a specific Sensor() instance, by port

    Returns: Sensor() instance, or None if instance is not found
    """

    s = [ x for x in __sensors__ if x.get_port() == port ]
    if len(s) > 1:
        raise ValueError("found %s instances of Sensor() with port %s, this should never happen" % (len(s), port))
    elif len(s) == 1:
        return s[0]
    else:
        return None


def add_sensor(
    self, 
    port, 
    pd_sck = None, 
    dout = None,
    offset_A = None,
    refunit_A = None,
    offset_B = None,
    refunit_B = None
):
    """Create a new sensor and add to the __sensors__ dict"""
    if not get_sensor(port):
        __sensors__.append(Sensor(*args, **kwargs))
    else:
        raise ValueError("Sensor at port %s already defined" % port)
