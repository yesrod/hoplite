
from .weighable import Weighable
import hoplite.utils as utils


class CO2(Weighable):

    def __init__(
        self, 
        sensor,
        channel,
        name,
        location = None,
        size = None,
        tare_wt = None,
        net_wt = None
    ):
        super().__init__(
            sensor,
            channel,
            name,
            utils.co2_data,
            location = location,
            size = size,
            tare_wt = tare_wt,
            net_wt = net_wt
        )
