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
                        fill_pct = utils.get_keg_fill_percent(w, cap, tare)

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
        keg_size_list = list(utils.keg_data)
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

            edit_keg_button = gui.Button('Edit', width=100, height=30, style={'margin': '3px'} )
            edit_keg_button.onclick.do(self.show_edit_keg, index, channel)
            keg_box.append(edit_keg_button, 'edit_keg')

            del_keg_button = gui.Button('Delete', width=100, height=30, style={'margin': '3px'} )
            del_keg_button.set_on_click_listener(self.show_delete_keg_confirm)
            keg_box.append(del_keg_button, 'del_keg')

        if readonly == True:
            keg_name_val.set_enabled(False)
            keg_size_val.set_enabled(False)
            custom_vol.set_enabled(False)
            custom_tare.set_enabled(False)
            co2_check.set_enabled(False)

        return keg_box


    def show_settings(self, widget):
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

        add_keg_button = gui.Button('Add Keg', width=100, height=30, style={'margin': '3px'} )
        add_keg_button.set_on_click_listener(self.show_edit_keg)
        self.settings_dialog.children['buttons_container'].add_child('add_keg', add_keg_button)

        self.settings_dialog.set_on_cancel_dialog_listener(self.cancel_settings)
        self.settings_dialog.set_on_confirm_dialog_listener(self.apply_settings)
        self.settings_dialog.show(self)


    def show_edit_keg(self, widget, index = None, channel = None):
        if self.edit_keg_up == True:
            return
        else:
            self.edit_keg_up = True

        hx_list = self.api_data['hx_list']

        self.edit_keg_dialog = gui.GenericDialog(title='Add/Edit Kegs',
                                                width='500px')

        port_list = [str(x) for x in list(utils.breakout_ports.keys()) + ['custom']]
        port_box = gui.HBox()
        port_menu = gui.DropDown.new_from_list(port_list)
        if index != None:
            port = utils.get_port_from_index(index, hx_list)
            port_menu.set_value(port)
        port_menu.set_on_change_listener(self.edit_keg_port_handler)
        port_label = gui.Label('Port')
        port_box.append(port_label, 0)
        port_box.append(port_menu, 1)
        self.edit_keg_dialog.add_field('port_box', port_box)

        hx_pins = gui.HBox()
        pd_sck = gui.TextInput(single_line=True, width = '50px', height='1.5em')
        pd_sck.set_enabled(False)
        pd_label = gui.Label('pd_sck')
        hx_pins.append(pd_label, 0)
        hx_pins.append(pd_sck, 1)
        dout = gui.TextInput(single_line=True, width = '50px', height='1.5em')
        dout.set_enabled(False)
        d_label = gui.Label('dout')
        hx_pins.append(d_label, 2)
        hx_pins.append(dout, 3)
        self.edit_keg_dialog.add_field('hx_pins', hx_pins)

        channel_box = gui.HBox()
        channel_menu = gui.DropDown.new_from_list(('A', 'B'))
        channel_menu.set_on_change_listener(self.edit_keg_channel_handler)
        if channel != None:
            channel_menu.set_value(channel)
        channel_label = gui.Label('Channel')
        channel_box.append(channel_label, 0)
        channel_box.append(channel_menu, 1)
        self.edit_keg_dialog.add_field('channel_box', channel_box)

        keg_box = self.build_keg_settings(channel, index)
        self.edit_keg_dialog.add_field('keg_box', keg_box)

        if index != None and channel != None:
            self.fill_edit_keg(index, channel)
            self.fill_port_info(index, channel)

        self.edit_keg_dialog.set_on_cancel_dialog_listener(self.cancel_edit_keg)
        self.edit_keg_dialog.children['buttons_container'].children['confirm_button'].onclick.do(self.apply_edit_keg, index, channel)
        self.edit_keg_dialog.show(self)


    def edit_keg_port_handler(self, widget, port):
        hx_list = self.api_data['hx_list']
        if port == 'custom':
            pd_sck =  self.edit_keg_dialog.get_field('hx_pins').children['1']
            dout = self.edit_keg_dialog.get_field('hx_pins').children['3']
            pd_sck.set_enabled(True)
            dout.set_enabled(True)
            custom_values = (pd_sck.get_value(), dout.get_value())
            index = utils.get_index_from_port(port, custom_values)
        else:
            pd_sck.set_enabled(False)
            dout.set_enabled(False)
            index = utils.get_index_from_port(port, hx_list)
        
        channel = self.edit_keg_dialog.get_field('channel_box').children['1'].get_value()

        self.fill_edit_keg(index, channel)
        self.fill_port_info(index, channel)


    def edit_keg_channel_handler(self, widget, channel):
        port = self.edit_keg_dialog.get_field('port_box').children['1'].get_value()
        hx_list = self.api_data['hx_list']
        index = utils.get_index_from_port(port, hx_list)

        self.fill_edit_keg(index, channel)


    def fill_edit_keg(self, index, channel, empty=False):
        new_conf = {}
        try:
            hx_conf = self.api_data['hx_list'][index]['channels'][channel]
            new_conf['volume'] = hx_conf['volume']
            new_conf['tare'] = hx_conf['tare']
            new_conf['name'] = hx_conf['name']
            new_conf['size'] = hx_conf['size']
            new_conf['co2'] = hx_conf['co2']
        except (KeyError, IndexError):
            new_conf['volume'] = ''
            new_conf['tare'] = ''
            new_conf['name'] = ''
            new_conf['size'] = ''
            new_conf['co2'] = False
        self.set_keg_gui_data(self.edit_keg_dialog, 'keg_box', new_conf)
        self.edit_keg_dialog.children['buttons_container'].children['confirm_button'].onclick.do(
            self.apply_edit_keg, index, channel)


    def fill_port_info(self, index, channel):
        try:
            hx_conf = self.api_data['hx_list'][index]
            self.edit_keg_dialog.get_field('hx_pins').children['1'].set_value(str(hx_conf.get('pd_sck', '')))
            self.edit_keg_dialog.get_field('hx_pins').children['3'].set_value(str(hx_conf.get('dout', '')))

        except (KeyError, IndexError):
            pass


    def show_delete_keg_confirm(self, widget):
        pass


    def cancel_settings(self, widget):
        self.settings_up = False


    def cancel_edit_keg(self, widget):
        self.edit_keg_up = False


    def cancel_delete_keg(self, widget):
        self.delete_keg_up = False


    def get_keg_gui_data(self, dialog, keg_box_id):
        keg_box = dialog.get_field(keg_box_id)

        new_name = keg_box.children['name'].children['val'].get_value()
        new_size = keg_box.children['size'].children['val'].get_value()
        new_co2 = keg_box.children['co2_box'].children['1'].get_value()

        if new_size == 'custom':
            vol = float(keg_box.children['custom'].children['1'].get_value())
            tare = float(keg_box.children['custom'].children['3'].get_value())
        else:
            vol = utils.keg_data[new_size][0]
            tare = utils.keg_data[new_size][1]

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
            keg_box.children['custom'].children['1'].set_value(str(utils.keg_data[new_conf['size']][0]))
            keg_box.children['custom'].children['3'].set_value(str(utils.keg_data[new_conf['size']][1]))


    def apply_settings(self, widget):
        self.settings_up = False

        weight_mode = self.settings_dialog.get_field('weight_options').get_value()
        self.api_write('PUT', 'weight_mode', {'weight_mode': weight_mode})


    def apply_edit_keg(self, widget, index, channel):
        self.edit_keg_up = False
        
        self.api_read(force=True)
        TempData = self.api_data

        hx_conf = TempData['hx_list'][index]['channels'][channel]

        try:
            new_conf = self.get_keg_gui_data(self.edit_keg_dialog, channel + '_box')
            hx_conf['name'] = new_conf['name']
            hx_conf['size'] = new_conf['size']
            hx_conf['volume'] = new_conf['volume']
            hx_conf['tare'] = new_conf['tare']
            hx_conf['co2'] = new_conf['co2']
            endpoint = 'hx/%s/%s/' % (str(index), channel)
            self.api_write('POST', endpoint, hx_conf['channels'][channel])
        except (KeyError, IndexError):
            pass


    def confirm_delete_keg(self, widget):
        pass


    def main(self):
        self.api_read()

        self.kegs = list()
        self.settings_up = False
        self.edit_keg_up = False
        self.delete_keg_up = False
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
        self.settings_button.set_on_click_listener(self.show_settings)
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
                    keg_fill_pct = utils.get_keg_fill_percent(
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
