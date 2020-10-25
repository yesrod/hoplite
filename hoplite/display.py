from luma.core import cmdline, error
from luma.core.render import canvas
from PIL import ImageFont
import sys

import luma.emulator.device
import pkg_resources

import hoplite.utils as utils

class Display():

    def __init__(self, hoplite, display, debug=False):
        self.display = display
        self.debug = debug
        self.h = hoplite

        resource_package = __name__
        resource_path = ''
        static_path = pkg_resources.resource_filename(resource_package, resource_path)

        self.font = ImageFont.truetype('%s/font/OpenSans-Regular.ttf' % static_path, 16)

        try:
            parser = cmdline.create_parser(description='HOPLITE display args')
            conf = cmdline.load_config('%s/conf/%s.conf' % (static_path, display))
            args = parser.parse_args(conf)
        except FileNotFoundError:
            conf = ['--display=%s' % display]
            args = parser.parse_args(conf)

        try:
            self.device = cmdline.create_device(args)
        except error.Error as e:
            parser.error(e)
            self.device = None


    def text_header(self, y, message, fill="white"):
        W = self.device.width
        w, h = self.draw.textsize(message)
        self.draw.text(((W-w)/2, y), message, fill=fill)


    def text_align_center(self, x, y, message, fill="white"):
        w, h = self.draw.textsize(message)
        self.draw.text((x-(w/2), y), message, fill=fill)


    def fill_bar(self, x, y, min_w, max_w, w, outline="white", fill=None):
        net_w = max(w - min_w, 0)
        max_net_w = max_w - min_w
        fill_percent = float(net_w) / float(max_net_w)
        max_y = self.device.height - 21
        min_y = y+1
        max_bar = max_y - min_y
        fill_height = max(min_y, min_y + (max_bar - (max_bar * fill_percent)))

        if fill == None:
            fill = self.fill_bar_color(fill_percent)

        self.draw.rectangle([x,y, x+20,self.device.height-20], outline=outline, fill="black")
        self.draw.rectangle([x+1,fill_height, x+19,max_y], outline=fill, fill=fill)
        utils.debug_msg(self, "%s: %s" % (fill_percent, fill)) 


    def fill_bar_color(self, percent):
        if percent > 0.5:
            return "green"
        if 0.5 > percent > 0.2:
            return "yellow"
        if 0.2 > percent:
            return "red"
        # default in case something breaks
        return "gray"


    def render(self, weight, mode, hx_conf):
        try:
            kegA = weight[0]
            kegA_name = hx_conf['channels']['A']['name'][0:13]
            kegA_min = hx_conf['channels']['A']['tare'] * 1000
            kegA_cap = hx_conf['channels']['A']['volume'] * 1000
            kegA_max = kegA_min + kegA_cap
        except (ValueError, KeyError):
            # no channel A data
            kegA = 0
            kegA_name = None
            kegA_min = 0
            kegA_cap = 0
            kegA_max = 0

        try:
            if hx_conf['channels']['A']['co2'] == True:
                kegA_name = None
        except KeyError:
            pass

        try:
            kegB = weight[1]
            kegB_name = hx_conf['channels']['B']['name'][0:13]
            kegB_min = hx_conf['channels']['B']['tare'] * 1000
            kegB_cap = hx_conf['channels']['B']['volume'] * 1000
            kegB_max = kegB_min + kegB_cap
        except (ValueError, KeyError):
            # no channel B data
            kegB = 0
            kegB_name = None
            kegB_min = 0
            kegB_cap = 0
            kegB_max = 0

        try:
            if hx_conf['channels']['B']['co2'] == True:
                kegB_name = None
        except KeyError:
            pass

        if kegA_name == None and kegB_name == None:
            return

        with canvas(self.device) as self.draw:
            utils.debug_msg(self, "%s: %s/%s  %s: %s/%s" % ( kegA_name, kegA, kegA_max, 
                                             kegB_name, kegB, kegB_max ))
            utils.debug_msg(self, "min: %s %s" % ( kegA_min, kegB_min ))
            self.text_header(0, "HOPLITE", fill="red")

            utils.debug_msg(self, "temp: %s" % utils.as_degF(self.h.temp))
            self.text_align_center(30, 0, utils.as_degF(self.h.temp), fill="blue")
            try:
                utils.debug_msg(self, "CO2: "+str(self.h.co2_w[0])+"%") #TODO: Handle multiple CO2 sources
                self.text_align_center(130, 0, "CO2: "+str(self.h.co2_w[0])+"%", fill="blue")
            except IndexError:
                utils.debug_msg(self, "CO2: N/A") #TODO: Handle multiple CO2 sources
                self.text_align_center(130, 0, "CO2: N/A", fill="blue")

            if kegA_name:
                self.text_align_center(40, 15, kegA_name)
                self.fill_bar(30, 35, kegA_min, kegA_max, kegA)
                self.text_align_center(40, self.device.height-10,
                                       utils.format_weight(kegA, mode, tare=kegA_min, cap=kegA_cap))

            if kegB_name:
                self.text_align_center(120, 15, kegB_name)
                self.fill_bar(110, 35, kegB_min, kegB_max, kegB)
                self.text_align_center(120, self.device.height-10,
                                       utils.format_weight(kegB, mode, tare=kegB_min, cap=kegB_cap))
