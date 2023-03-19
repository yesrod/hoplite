

class Weighable():

    def __init__(
        self, 
        sensor,
        channel,
        name,
        weight_data,
        location = None,
        size = None,
        tare_wt = None,
        net_wt = None
    ):
        self.sensor = sensor    # this is a Sensor() instance, already set up
        self.set_channel(channel)
        self.set_name(name)
        self.set_location(location)
        self.weight_data = weight_data
        self.set_size(size, tare_wt=tare_wt, net_wt=net_wt)

        # weight_data must be set for subclasses
        # set it in the subclass's __init__ function
        # then call super().__init__(port, channel)
        #
        # def __init__(self, ...)
        #     self.weight_data = utils.foo_data
        #     super().__init__(...)


    def get_weight(self):
        return self.sensor.get_weight(self.channel)


    def tare(self):
        self.sensor.tare_channel(self.channel)


    def calibrate(self, cal_weight):
        self.sensor.calibrate_channel(self.channel, cal_weight)


    def get_name(self):
        return self.name


    def set_name(self, name):
        self.name = name


    def get_location(self):
        return self.location


    def set_location(self, location):
        self.location = location


    def get_size(self):
        return (self.size, self.tare_wt, self.net_wt)


    def set_size(self, size, tare_wt=None, net_wt=None):
        # TODO: function logic
        # if size is set, pick size, tare_wt, net_wt from size dict
        # else, set size to "custom", set tare_wt and net_wt from parameters
        # then update Sensor() instance as necessary
        try:
            self.size = size
            self.tare_wt, self.net_wt = self.weight_data[size]
        except KeyError:    # size key not found in weight_data
            self.size = 'custom'
            if not tare_wt or not net_wt:
                raise ValueError(f"non-standard size {size} requires tare_wt and net_wt, found instead {tare_wt} and {net_wt}")
            self.tare_wt = tare_wt
            self.net_wt = net_wt


    def get_channel(self):
        return self.channel


    def set_channel(self, channel):
        if channel in ('A', 'B'):
            self.channel = channel
        else:
            raise ValueError("no such channel %s" % channel)
