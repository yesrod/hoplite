import remi.gui as gui
from remi import start, App

import sys
import time
import json
import mmap
import pkg_resources
import requests

from .hoplite import Hoplite
import hoplite.utils as utils


class Web(App):

    def __init__(self, *args):
        self.h = Hoplite()
        self.debug = False

        self.api_url = "http://127.0.0.1:5000/v1/"
        self.api_data = {}
        self.api_last_updated = 1
        self.api_update_interval = 5

        self.co2_list = []

        resource_package = __name__
        resource_path = '/static'
        static_path = pkg_resources.resource_filename(
            resource_package, resource_path)

        static_file_path = {
            'static': static_path
        }

        super(Web, self).__init__(*args, static_file_path=static_file_path)


    def api_read(self, force = False):
        since_last_update = int(time.time()) - self.api_last_updated
        if since_last_update > self.api_update_interval or force:
            response = requests.get(self.api_url)
            self.api_data = response.json()['data']['v1']
            self.api_last_updated = int(time.time())
            utils.debug_msg(self, "api_data: %s" % self.api_data)
        else:
            utils.debug_msg(self, "not updating, last update %is ago" % since_last_update)


    def api_write(self, mode, endpoint, data):
        headers = {'Content-Type': 'application/json'}
        dest_url = self.api_url + endpoint
        if mode == 'POST':
            response = requests.post(dest_url, data = json.dumps(data), headers = headers)
        elif mode == 'PUT':
            response = requests.put(dest_url, data = json.dumps(data), headers = headers)
        else:
            utils.debug_msg(self, "ERROR: bad HTTP mode")
            return
        if response.status_code != "200":
            utils.debug_msg(self, "response: %s" % response.json())
            utils.debug_msg(self, dest_url)
            utils.debug_msg(self, json.dumps(data))


    def get_keg_fill_percent(self, w, cap, tare):
        keg_cap = cap * 1000
        keg_tare = tare * 1000
        net_w = max((w - keg_tare), 0)
        fill_percent = net_w / keg_cap
        return fill_percent


    def idle(self):
        self.api_read()

        w_mode = self.api_data.get('weight_mode', 'as_kg_gross')

        self.co2_list = []

        for line in self.kegs:
            if line == None:
                continue
            for hx_conf in self.api_data['hx_list']:
                for channel in ['A', 'B']:
                    # handle co2
                    try:
                        if hx_conf['channels'][channel]['co2'] == True:
                            local_w = hx_conf['channels'][channel]['weight']
                            local_max = hx_conf['channels'][channel]['volume'] * 1000
                            local_tare = hx_conf['channels'][channel]['tare'] * 1000
                            local_net_w = max((local_w - local_tare), 0) 
                            local_pct = local_net_w / float(local_max)
                            self.co2_list.append(int(local_pct * 100))
                            continue
                    except KeyError:
                        pass

                    # channel update
                    try:
                        w = hx_conf['channels'][channel]['weight']
                        cap = hx_conf['channels'][channel]['volume']
                        tare = hx_conf['channels'][channel]['tare']
                        name = hx_conf['channels'][channel]['name']
                        fill_pct = self.get_keg_fill_percent(w, cap, tare)

                        line[0].set_text(name)
                        line[1].set_size(240 * fill_pct, 30)
                        line[1].style[
                            'fill'] = utils.fill_bar_color(fill_pct)
                        line[2].set_text(utils.format_weight(
                            w, w_mode, tare=(tare * 1000), cap=(cap * 1000)))
                    except (KeyError, IndexError):
                        pass

        t = utils.as_degF(self.api_data.get('temp', 0))
        try:
            co2 = self.co2_list[0] #TODO: Handle multiple CO2 sources
        except IndexError:
            co2 = "???"
        self.temp.set_text("%s\nCO2:%s%%" % (t, co2))


    def close(self):
        super(Web, self).close()


    def build_keg_settings(self, channel, index = None, hx_conf = None, readonly = False):
        keg_size_list = list(self.h.keg_data)
        keg_size_list.append('custom')

        keg_box_style = {'border': '2px solid lightgrey', 'border-radius': '5px'}
        keg_box = gui.Container(style=keg_box_style)

        box_name = gui.Label('Channel ' + channel)
        keg_box.append(box_name)

        keg_name = gui.HBox()
        keg_name_lbl = gui.Label('Keg Name', width='20%')
        keg_name.append(keg_name_lbl, 'lbl')
        keg_name_val = gui.TextInput(single_line=True, height='1.5em')
        keg_name.append(keg_name_val, 'val')
        keg_box.append(keg_name, 'name')

        keg_size = gui.HBox()
        keg_size_lbl = gui.Label('Keg Size', width='20%')
        keg_size.append(keg_size_lbl, 'lbl')
        keg_size_val = gui.DropDown.new_from_list(keg_size_list)
        keg_size.append(keg_size_val, 'val')
        keg_box.append(keg_size, 'size')

        custom = gui.HBox()
        vol_lbl = gui.Label('Volume (l)', width='20%')
        custom.append(vol_lbl, 0)
        custom_vol = gui.TextInput(
            single_line=True, height='1.5em', width='30%')
        custom.append(custom_vol, 1)
        tare_lbl = gui.Label('Empty Weight (kg)', width='30%')
        custom.append(tare_lbl, 2)
        custom_tare = gui.TextInput(
            single_line=True, height='1.5em', width='20%')
        custom.append(custom_tare, 3)

        keg_box.append(custom, 'custom')

        co2_box = gui.HBox(width='20%')
        co2_label = gui.Label('CO2')
        co2_box.append(co2_label, 0)
        co2_check = gui.CheckBox('CO2', False)
        co2_box.append(co2_check, 1)
        keg_box.append(co2_box, 'co2_box')

        if hx_conf != None and index != None:
            cap = hx_conf['channels'][channel]['volume']
            tare = hx_conf['channels'][channel]['tare']
            name = hx_conf['channels'][channel]['name']
            size_name = hx_conf['channels'][channel]['size']
            co2 = hx_conf['channels'][channel]['co2']

            box_name.set_text('Sensor ' + str(index) + ' Channel ' + channel)
            keg_name_val.set_value(name)
            keg_size_val.select_by_value(size_name)
            custom_vol.set_value(str(cap))
            custom_tare.set_value(str(tare))
            co2_check.set_value(co2)

            del_keg_button = gui.Button('Delete Keg', width=100, height=30, style={'margin': '3px'} )
            del_keg_button.set_on_click_listener(self.show_del_keg_confirm)
            keg_box.append(del_keg_button, 'del_keg')

        if readonly == True:
            keg_name_val.set_enabled(False)
            keg_size_val.set_enabled(False)
            custom_vol.set_enabled(False)
            custom_tare.set_enabled(False)
            co2_check.set_enabled(False)

        return keg_box


    def show_settings_menu(self, widget):
        if self.settings_up == True:
            return
        else:
            self.settings_up = True

        self.api_read(force=True)

        self.settings_dialog = gui.GenericDialog(title='Settings',
                                        width='500px')

        # weight display options
        weight_options_list = ['as_kg_gross', 'as_kg_net', 'as_pint', 'as_pct']
        weight_options = gui.DropDown.new_from_list(weight_options_list)
        try:
            weight_options.select_by_value(self.api_data['weight_mode'])
        except (KeyError, IndexError):
            pass
        self.settings_dialog.add_field_with_label(
            'weight_options', 'Display Keg Weight', weight_options)

        for index, hx_conf in enumerate(self.api_data['hx_list']):
            for channel in ('A', 'B'):
                try:
                    keg_box = self.build_keg_settings(channel, index, hx_conf, readonly=True)
                    self.settings_dialog.add_field(str(index) + channel + '_box', keg_box)
                except (KeyError, IndexError):
                    pass

        add_keg_button = gui.Button('Add/Edit Keg', width=100, height=30, style={'margin': '3px'} )
        add_keg_button.set_on_click_listener(self.show_add_keg_menu)
        self.settings_dialog.children['buttons_container'].add_child('add_keg', add_keg_button)

        self.settings_dialog.set_on_cancel_dialog_listener(self.cancel_settings)
        self.settings_dialog.set_on_confirm_dialog_listener(self.apply_settings)
        self.settings_dialog.show(self)


    def show_add_keg_menu(self, widget):
        if self.add_keg_up == True:
            return
        else:
            self.add_keg_up = True

        hx_conf = self.api_data['hx_list']

        self.add_keg_dialog = gui.GenericDialog(title='Add/Edit Kegs',
                                                width='500px')

        index_list = [str(x) for x in list(range(0,len(hx_conf))) + ['new']]
        index_box = gui.HBox()
        index_menu = gui.DropDown.new_from_list(index_list)
        index_menu.set_on_change_listener(self.fill_add_keg)
        index_label = gui.Label('Sensor Index')
        index_box.append(index_label, 0)
        index_box.append(index_menu, 1)
        self.add_keg_dialog.add_field('index_box', index_box)

        hx_pins = gui.HBox()
        pd_sck = gui.TextInput(single_line=True, height='1.5em')
        pd_label = gui.Label('pd_sck')
        hx_pins.append(pd_label, 0)
        hx_pins.append(pd_sck, 1)
        d_out = gui.TextInput(single_line=True, height='1.5em')
        d_label = gui.Label('d_out')
        hx_pins.append(d_label, 2)
        hx_pins.append(d_out, 3)

        self.add_keg_dialog.add_field('hx_pins', hx_pins)
        
        for channel in ('A', 'B'):
            keg_box = self.build_keg_settings(channel)
            self.add_keg_dialog.add_field(channel + '_box', keg_box)

        self.add_keg_dialog.set_on_cancel_dialog_listener(self.cancel_add_keg)
        self.add_keg_dialog.set_on_confirm_dialog_listener(self.apply_add_keg)
        self.add_keg_dialog.show(self)


    def fill_add_keg(self, widget, index_menu):
        utils.debug_msg(self, "index_menu: %s" % index_menu)
        if index_menu == 'new':
            # TODO: Clear all keg add/edit GUI fields
            pass
        else:
            index = int(index_menu)
            utils.debug_msg(self, "index: %s" % index)
            hx_conf = self.api_data['hx_list'][index]
            for channel in ('A', 'B'):
                try:
                    new_conf = {}
                    new_conf['volume'] = hx_conf['channels'][channel]['volume']
                    new_conf['tare'] = hx_conf['channels'][channel]['tare']
                    new_conf['name'] = hx_conf['channels'][channel]['name']
                    new_conf['size'] = hx_conf['channels'][channel]['size']
                    new_conf['co2'] = hx_conf['channels'][channel]['co2']
                    self.set_keg_gui_data(self.add_keg_dialog, channel + '_box', new_conf)

                except (KeyError, IndexError):
                    pass


    def show_del_keg_confirm(self, widget):
        pass


    def cancel_settings(self, widget):
        self.settings_up = False


    def cancel_add_keg(self, widget):
        self.add_keg_up = False


    def get_keg_gui_data(self, dialog, keg_box_id):
        keg_box = dialog.get_field(keg_box_id)

        new_name = keg_box.children['name'].children['val'].get_value()
        new_size = keg_box.children['size'].children['val'].get_value()
        new_co2 = keg_box.children['co2_box'].children['1'].get_value()

        if new_size == 'custom':
            vol = float(keg_box.children['custom'].children['1'].get_value())
            tare = float(keg_box.children['custom'].children['3'].get_value())
        else:
            vol = self.h.keg_data[new_size][0]
            tare = self.h.keg_data[new_size][1]

        new_conf = dict()
        new_conf['name'] = new_name
        new_conf['size'] = new_size
        new_conf['volume'] = vol
        new_conf['tare'] = tare
        new_conf['co2'] = new_co2
        return new_conf


    def set_keg_gui_data(self, dialog, keg_box_id, new_conf):
        utils.debug_msg(self, "new_conf: %s" % new_conf)
        utils.debug_msg(self, "keg_box_id: %s" % keg_box_id)
        keg_box = dialog.get_field(keg_box_id)

        keg_box.children['name'].children['val'].set_value(new_conf['name'])
        keg_box.children['size'].children['val'].set_value(new_conf['size'])
        keg_box.children['co2_box'].children['1'].set_value(new_conf['co2'])

        if new_conf['size'] == 'custom':
            keg_box.children['custom'].children['1'].set_value(str(new_conf['volume']))
            keg_box.children['custom'].children['3'].set_value(str(new_conf['tare']))
        else:
            keg_box.children['custom'].children['1'].set_value(str(self.h.keg_data[new_conf['size']][0]))
            keg_box.children['custom'].children['3'].set_value(str(self.h.keg_data[new_conf['size']][1]))


    def apply_settings(self, widget):
        self.settings_up = False

        weight_mode = self.settings_dialog.get_field('weight_options').get_value()
        self.api_write('PUT', 'weight_mode', {'weight_mode': weight_mode})


    def apply_add_keg(self, widget):
        self.add_keg_up = False
        
        self.api_read(force=True)
        TempData = self.api_data

        for index, hx_conf in enumerate(TempData['hx_list']):
            for channel in ('A', 'B'):
                try:
                    new_conf = self.get_keg_gui_data(self.add_keg_dialog, channel + '_box')
                    hx_conf['channels'][channel]['name'] = new_conf['name']
                    hx_conf['channels'][channel]['size'] = new_conf['size']
                    hx_conf['channels'][channel]['volume'] = new_conf['volume']
                    hx_conf['channels'][channel]['tare'] = new_conf['tare']
                    hx_conf['channels'][channel]['co2'] = new_conf['co2']
                    endpoint = 'hx/%s/%s/' % (str(index), channel)
                    self.api_write('POST', endpoint, hx_conf['channels'][channel])
                except (KeyError, IndexError):
                    pass


    def main(self):
        self.api_read()

        self.kegs = list()
        self.settings_up = False
        self.add_keg_up = False
        self.co2_list = []

        # root object
        self.container = gui.Table(width=480)
        self.container.style['margin'] = 'auto'
        self.container.style['text-align'] = 'center'
        self.container.style['padding'] = '2em'

        # first row
        first_row = gui.TableRow(height=60)

        # temperature
        t = utils.as_degF(self.api_data.get('temp', 0))
        self.temp = gui.Label("%s<br />CO2:%s%%" % (t, '???'))
        self.temp.style['padding-bottom'] = '1em'
        self.temp.style['white-space'] = 'pre'
        table_item = gui.TableItem()
        table_item.append(self.temp)
        first_row.append(table_item)

        # title
        self.title = gui.Label("HOPLITE")
        self.title.style['font-size'] = '2em'
        self.title.style['padding-bottom'] = '0.5em'
        table_item = gui.TableItem()
        table_item.append(self.title)
        first_row.append(table_item)

        # settings button
        self.settings_button = gui.Image('/static:settings_16.png', width=16)
        self.settings_button.set_on_click_listener(self.show_settings_menu)
        self.settings_button.style['padding-bottom'] = '1.6em'
        table_item = gui.TableItem()
        table_item.append(self.settings_button)
        first_row.append(table_item)

        self.container.append(first_row)

        w_mode = self.api_data.get('weight_mode', 'as_kg_gross')

        # iterate through HX sensors
        for index, hx_conf in enumerate(self.api_data['hx_list']):

            self.kegs.insert(index, None)

            # keg information
            for channel in ['A', 'B']:
                try:
                    keg_name = hx_conf['channels'][channel].get('name', None)
                except KeyError:
                    keg_name = None
                try:
                    if hx_conf['channels'][channel]['co2'] == True:
                        local_w = hx_conf['channels'][channel]['weight']
                        local_max = hx_conf['channels'][channel]['volume'] * 1000
                        local_tare = hx_conf['channels'][channel]['tare'] * 1000
                        local_net_w = max((local_w - local_tare), 0) 
                        local_pct = local_net_w / float(local_max)
                        self.co2_list.append(int(local_pct * 100))
                        continue
                except KeyError:
                    pass

                if keg_name != None:
                    keg_label = gui.Label(keg_name, width=100, height=30)

                    keg_bar = gui.Svg(width=240, height=30)
                    keg_w = hx_conf['channels'][channel]['weight']
                    keg_cap = hx_conf['channels'][channel]['volume']
                    keg_tare = hx_conf['channels'][channel]['tare']
                    keg_fill_pct = self.get_keg_fill_percent(
                        keg_w, keg_cap, keg_tare)
                    keg_bar_rect = gui.SvgRectangle(0, 0, 240 * keg_fill_pct, 30)
                    keg_bar_rect.style[
                        'fill'] = utils.fill_bar_color(keg_fill_pct)
                    keg_bar_outline = gui.SvgRectangle(0, 0, 240, 30)
                    keg_bar_outline.style['fill'] = 'rgb(0,0,0)'
                    keg_bar_outline.style['fill-opacity'] = '0'
                    keg_bar.append(keg_bar_rect)
                    keg_bar.append(keg_bar_outline)

                    keg_weight = gui.Label(utils.format_weight(
                        keg_w, w_mode, tare=(keg_tare * 1000), cap=(keg_cap * 1000)), 
                        width=100, height=30)

                    self.kegs.insert(
                        index, [keg_label, keg_bar_rect, keg_weight])

                    table_row = gui.TableRow(height=30)
                    for item in [keg_label, keg_bar, keg_weight]:
                        table_item = gui.TableItem()
                        table_item.append(item)
                        table_row.append(table_item)

                    self.container.append(table_row)

        try:
            co2 = self.co2_list[0] #TODO: Handle multiple CO2 sources
        except IndexError:
            co2 = "???"
        self.temp.set_text("%s\nCO2:%s%%" % (t, co2))

        # return of the root widget
        return self.container


if __name__ == '__main__':
    start(Web, address="0.0.0.0", port=80,
          standalone=False, update_interval=0.5,
          title='HOPLITE')
