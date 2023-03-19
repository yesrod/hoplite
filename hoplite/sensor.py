import time
from hx711 import HX711


class Sensor():

    # Breakout board port data
    # Value is list( pd_sck, dout )
    breakout_ports = {
        1: (6, 5),
        2: (13, 12),
        3: (27, 17),
        4: (25, 22),
    }

    def __init__(
        self,
        port,
        offset_A = None,
        refunit_A = None,
        offset_B = None,
        refunit_B = None
    ):

        self.port = port
        self.set_port(self.port)

        self.offset_A = offset_A
        self.refunit_A = refunit_A

        self.offset_B = offset_B
        self.refunit_B = refunit_B

        self.weight_A = 0.0
        self.weight_B = 0.0

        self.__init_hx711()
        self.__hx711_apply_changes()

        self.last_updated = 0.0


    def poll(self):
        self.weight_A, self.weight_B = self.__read_weight()
        self.last_updated = time.time()


    def get_weight(self, channel):
        if channel == 'A':
            return self.weight_A
        elif channel == 'B':
            return self.weight_B
        else:
            raise ValueError("no such channel %s" % channel)


    def tare_channel(self, channel):
        # TODO: copy and adapt tare logic from __main__.py
        pass


    def calibrate_channel(self, channel):
        # TODO: copy and adapt calibration logic from __main__.py
        pass


    def set_port(self, port):
        if port in self.breakout_ports.keys():
            self.pd_sck = self.breakout_ports[port][0]
            self.dout = self.breakout_ports[port][1]
        else:
            raise ValueError("bad port %s" % port)


    def get_port(self):
        return self.port


    def __init_hx711(self):
        self.hx = HX711(self.dout, self.pd_sck)
        self.hx.set_reading_format("MSB", "MSB")
        self.hx.reset()


    def __hx711_read_ch(self, channel):
        if channel == 'A':
            return int(self.hx.get_weight_A(5))
        elif channel == 'B':
            return int(self.hx.get_weight_B(5))
        else:
            raise ValueError("no such channel %s" % channel)

    
    def __hx711_read_chA(self):
        return int(self.hx.get_weight_A(5))

    
    def __hx711_read_chB(self):
        return int(self.hx.get_weight_B(5))


    def __hx711_cal_chA(self, real_w):
        ref = self.hx.REFERENCE_UNIT
        self.hx.set_reference_unit_A(1)
        raw_w = self.hx.get_weight_A(7)
        self.hx.set_reference_unit_A(ref)
        return raw_w / float(real_w)


    def __hx711_cal_chB(self, real_w):
        ref = self.hx.REFERENCE_UNIT_B
        self.hx.set_reference_unit_B(1)
        raw_w = self.hx.get_weight_B(7)
        self.hx.set_reference_unit_B(ref)
        return raw_w / float(real_w)


    def __read_weight(self):
        self.hx.reset()
        chA = self.__hx711_read_chA()
        chB = self.__hx711_read_chB()
        return ( chA, chB )


    def __set_offset(self, channel, offset):
        if channel == 'A':
            self.offset_A = offset
            self.hx.set_offset_A(offset)
        elif channel == 'B':
            self.offset_B = offset
            self.hx.set_offset_B(offset)
        else:
            raise ValueError("no such channel %s" % channel)


    def __get_offset(self, channel):
        if channel == 'A':
            return self.offset_A
        elif channel == 'B':
            return self.offset_B
        else:
            raise ValueError("no such channel %s" % channel)


    def __set_refunit(self, channel, refunit):
        if channel == 'A':
            self.refunit_A = refunit
            self.hx.set_reference_unit_A(self.refunit_A)
        elif channel == 'B':
            self.refunit_B = refunit
            self.hx.set_reference_unit_B(self.refunit_B)
        else:
            raise ValueError("no such channel %s" % channel)


    def __get_refunit(self, channel):
        if channel == 'A':
            return self.refunit_A
        elif channel == 'B':
            return self.refunit_B
        else:
            raise ValueError("no such channel %s" % channel)


    def __hx711_apply_changes(self):
        for ch in ('A', 'B'):
            offset = self.__get_offset(ch)
            refunit = self.__get_refunit(ch)
            if offset is not None and refunit is not None: 
                try:
                    self.__set_refunit(ch, refunit)
                except ValueError:
                    print("Bad channel A reference unit %s, using 1" % refunit)
                    self.__set_refunit(ch, 1)
                self.__set_offset(ch, offset)
            else:
                self.__set_refunit(ch, 1)

        self.hx.reset()
