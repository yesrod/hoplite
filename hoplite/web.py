import remi.gui as gui
from remi import start, App

import time
import json
import pkg_resources
import requests
import argparse

from .hoplite import Hoplite
import hoplite.utils as utils


class Web(App):

    def __init__(self, *args):
        self.h = Hoplite()

        resource_package = __name__
        resource_path = '/static'
        static_path = pkg_resources.resource_filename(
            resource_package, resource_path)

        static_file_path = {
            'static': static_path
        }

        super(Web, self).__init__(*args, static_file_path=static_file_path)


    def api_read(self, force = False):
        utils.debug_msg(self, "start")
        since_last_update = int(time.time()) - self.api_last_updated
        if since_last_update > self.api_update_interval or force:
            response = requests.get(self.api_url)
            self.api_data = response.json()['data']['v1']
            self.api_last_updated = int(time.time())
            utils.debug_msg(self, "api_data: %s" % self.api_data)
        else:
            utils.debug_msg(self, "not updating, last update %is ago" % since_last_update)
        utils.debug_msg(self, "end")


    def api_write(self, mode, endpoint, data):
        utils.debug_msg(self, "start")
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
        utils.debug_msg(self, "end")


    def api_delete(self, endpoint):
        utils.debug_msg(self, "start")
        headers = {'Content-Type': 'application/json'}
        dest_url = self.api_url + endpoint
        response = requests.delete(dest_url, headers = headers)
        if response.status_code != "200":
            utils.debug_msg(self, "response: %s" % response.json())
            utils.debug_msg(self, dest_url)
        utils.debug_msg(self, "end")


    def idle(self):
        utils.debug_msg(self, "start")

        self.api_read()
        self.co2_list = []
        self.container.children['keg_table'] = self.build_keg_table()
        t = utils.as_degF(self.api_data.get('temp', 0))
        try:
            co2 = self.co2_list[0] #TODO: Handle multiple CO2 sources
        except IndexError:
            co2 = "???"
        self.temp.set_text("%s\nCO2:%s%%" % (t, co2))

        utils.debug_msg(self, "end")


    def close(self):
        utils.debug_msg(self, "closing")
        super(Web, self).close()


    def build_keg_settings(self, index = None, channel = None, chan_conf = None, readonly = False, edit = False):
        utils.debug_msg(self, "start")

        keg_box_style = {'border': '2px solid lightgrey', 'border-radius': '5px'}
        keg_box = gui.Container(style=keg_box_style)
        utils.debug_msg(self, "keg_box")

        box_name = gui.Label('Channel')
        keg_box.append(box_name)
        utils.debug_msg(self, "box_name")

        keg_name = gui.HBox()
        keg_name_lbl = gui.Label('Keg Name', width='20%')
        keg_name.append(keg_name_lbl, 'lbl')
        keg_name_val = gui.TextInput(single_line=True, height='1.5em')
        keg_name.append(keg_name_val, 'val')
        keg_box.append(keg_name, 'name')
        utils.debug_msg(self, "keg_name")

        keg_size_list = list(utils.keg_data)
        keg_size_list.append('custom')
        keg_size_list.insert(0, '')
        utils.debug_msg(self, "keg_size_list")

        keg_size = gui.HBox()
        keg_size_lbl = gui.Label('Keg Size', width='20%')
        keg_size.append(keg_size_lbl, 'lbl')
        keg_size_val = gui.DropDown.new_from_list(keg_size_list)
        keg_size_val.set_value('')
        keg_size.append(keg_size_val, 'val')
        keg_box.append(keg_size, 'size')
        utils.debug_msg(self, "keg_size")

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
        utils.debug_msg(self, "custom_size")

        co2_box = gui.HBox(width='20%')
        co2_label = gui.Label('CO2')
        co2_box.append(co2_label, 0)
        co2_check = gui.CheckBox('CO2', False)
        co2_box.append(co2_check, 1)
        keg_box.append(co2_box, 'co2_box')
        utils.debug_msg(self, "co2_box")

        if chan_conf != None and index != None and channel != None:
            utils.debug_msg(self, "populating keg info")
            cap = chan_conf['volume']
            tare = chan_conf['tare']
            name = chan_conf['name']
            size_name = chan_conf['size']
            co2 = chan_conf['co2']

            box_name.set_text('Sensor ' + str(index) + ' Channel ' + channel)
            keg_name_val.set_value(name)
            keg_size_val.select_by_value(size_name)
            custom_vol.set_value(str(cap))
            custom_tare.set_value(str(tare))
            co2_check.set_value(co2)
            utils.debug_msg(self, "end populating keg info")

        if edit != False:
            utils.debug_msg(self, "edit and delete buttons")
            edit_keg_button = gui.Button('Edit', width=100, height=30, style={'margin': '3px'} )
            edit_keg_button.onclick.do(self.show_edit_keg, index, channel)
            keg_box.append(edit_keg_button, 'edit_keg')
            utils.debug_msg(self, "edit button")

            del_keg_button = gui.Button('Delete', width=100, height=30, style={'margin': '3px'} )
            del_keg_button.onclick.do(self.show_delete_keg_confirm, index, channel)
            keg_box.append(del_keg_button, 'del_keg')
            utils.debug_msg(self, "delete button")

        if readonly == True:
            utils.debug_msg(self, "settings are readonly")
            keg_name_val.set_enabled(False)
            keg_size_val.set_enabled(False)
            custom_vol.set_enabled(False)
            custom_tare.set_enabled(False)
            co2_check.set_enabled(False)

        utils.debug_msg(self, "end")
        return keg_box


    def show_settings(self, widget):
        utils.debug_msg(self, "start")
        if self.settings_up == True:
            utils.debug_msg(self, "show_settings already up")
            return
        else:
            self.settings_up = True

        self.api_read(force=True)

        self.settings_dialog = gui.GenericDialog(title='Settings',
                                        width='500px')
        utils.debug_msg(self, "settings_dialog")

        # weight display options
        weight_options_list = ['as_kg_gross', 'as_kg_net', 'as_pint', 'as_pct']
        weight_options = gui.DropDown.new_from_list(weight_options_list)
        try:
            weight_options.select_by_value(self.api_data['weight_mode'])
        except (KeyError, IndexError):
            pass
        self.settings_dialog.add_field_with_label(
            'weight_options', 'Display Keg Weight', weight_options)
        utils.debug_msg(self, "weight_options")

        for index, hx_conf in enumerate(self.api_data['hx_list']):
            for channel in ('A', 'B'):
                try:
                    chan_conf = hx_conf['channels'][channel]
                    keg_box = self.build_keg_settings(index, channel, chan_conf, readonly=True, edit=True)
                    self.settings_dialog.add_field(str(index) + channel + '_box', keg_box)
                    utils.debug_msg(self, "index %s channel %s" % (index, channel))
                except (KeyError, IndexError):
                    pass

        add_keg_button = gui.Button('Add/Edit Keg', width=100, height=30, style={'margin': '3px'} )
        add_keg_button.set_on_click_listener(self.show_edit_keg)
        self.settings_dialog.children['buttons_container'].add_child('add_keg', add_keg_button)
        utils.debug_msg(self, "add_keg_button")

        self.settings_dialog.set_on_cancel_dialog_listener(self.cancel_settings)
        self.settings_dialog.set_on_confirm_dialog_listener(self.apply_settings)
        self.settings_dialog.show(self)
        utils.debug_msg(self, "end")


    def show_edit_keg(self, widget, index = None, channel = None):
        utils.debug_msg(self, "start")
        if self.edit_keg_up == True:
            utils.debug_msg(self, "edit_keg already up")
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

        keg_box = self.build_keg_settings(index, channel)
        self.edit_keg_dialog.add_field('keg_box', keg_box)

        if index != None and channel != None:
            self.fill_edit_keg(index, channel)
            self.fill_port_info(index, port_menu.get_value())

        self.edit_keg_dialog.set_on_cancel_dialog_listener(self.cancel_edit_keg)
        self.edit_keg_dialog.set_on_confirm_dialog_listener(self.apply_edit_keg)
        self.edit_keg_dialog.show(self)

        utils.debug_msg(self, "end")


    def edit_keg_port_handler(self, widget, port):
        utils.debug_msg(self, "start")
        hx_list = self.api_data['hx_list']
        pd_sck = self.edit_keg_dialog.get_field('hx_pins').children['1']
        dout = self.edit_keg_dialog.get_field('hx_pins').children['3']
        if port == 'custom':
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
        self.fill_port_info(index, port)
        utils.debug_msg(self, "end")


    def edit_keg_channel_handler(self, widget, channel):
        utils.debug_msg(self, "start")
        port = self.edit_keg_dialog.get_field('port_box').children['1'].get_value()
        hx_list = self.api_data['hx_list']
        index = utils.get_index_from_port(port, hx_list)

        self.fill_edit_keg(index, channel)
        utils.debug_msg(self, "end")


    def fill_edit_keg(self, index, channel, empty=False):
        utils.debug_msg(self, "start")
        new_conf = {}
        try:
            hx_conf = self.api_data['hx_list'][index]['channels'][channel]
            new_conf['volume'] = hx_conf['volume']
            new_conf['tare'] = hx_conf['tare']
            new_conf['name'] = hx_conf['name']
            new_conf['size'] = hx_conf['size']
            new_conf['co2'] = hx_conf['co2']
        except (KeyError, IndexError, TypeError):
            new_conf['volume'] = ''
            new_conf['tare'] = ''
            new_conf['name'] = ''
            new_conf['size'] = ''
            new_conf['co2'] = False
        self.set_keg_gui_data(self.edit_keg_dialog, 'keg_box', new_conf)
        self.edit_keg_dialog.set_on_confirm_dialog_listener(self.apply_edit_keg)
        utils.debug_msg(self, "end")


    def fill_port_info(self, index, port):
        utils.debug_msg(self, "start")
        try:
            hx_conf = self.api_data['hx_list'][index]
            self.edit_keg_dialog.get_field('hx_pins').children['1'].set_value(str(hx_conf.get('pd_sck', '')))
            self.edit_keg_dialog.get_field('hx_pins').children['3'].set_value(str(hx_conf.get('dout', '')))

        except (KeyError, IndexError, TypeError):
            if port != "custom":
                self.edit_keg_dialog.get_field('hx_pins').children['1'].set_value(str(utils.breakout_ports[port][0]))
                self.edit_keg_dialog.get_field('hx_pins').children['3'].set_value(str(utils.breakout_ports[port][1]))
        utils.debug_msg(self, "end")


    def show_delete_keg_confirm(self, widget, index, channel):
        utils.debug_msg(self, "start")
        if self.delete_keg_up == True:
            return
        else:
            self.delete_keg_up = True

        self.delete_keg_dialog = gui.GenericDialog(title='DELETE Keg?', width=240)
        warning_label = gui.Label("Are you sure you want to delete keg at index %s channel %s?" % (index, channel))
        self.delete_keg_dialog.append(warning_label)
        self.delete_keg_dialog.set_on_cancel_dialog_listener(self.cancel_delete_keg)
        self.delete_keg_dialog.children['buttons_container'].children['confirm_button'].onclick.do(self.delete_keg, index, channel)
        self.delete_keg_dialog.show(self)
        utils.debug_msg(self, "end")


    def delete_keg(self, widget, index, channel):
        utils.debug_msg(self, "start")
        self.delete_keg_up = False
        self.delete_keg_dialog.hide()
        if len(self.api_data['hx_list'][index]['channels'].keys()) <= 1:
            endpoint = 'hx/%s/' % str(index)
            self.api_delete(endpoint)
        else:
            endpoint = 'hx/%s/%s/' % (str(index), channel)
            self.api_delete(endpoint)
        utils.debug_msg(self, "end")


    def cancel_settings(self, widget):
        self.settings_up = False


    def cancel_edit_keg(self, widget):
        self.edit_keg_up = False


    def cancel_delete_keg(self, widget):
        self.delete_keg_up = False


    def get_keg_gui_data(self, dialog, keg_box_id):
        utils.debug_msg(self, "start")
        keg_box = dialog.get_field(keg_box_id)
        utils.debug_msg(self, "keg_box: %s" % keg_box) 

        new_size = keg_box.children['size'].children['val'].get_value() # this takes forever sometimes to actually select, need to investigate
        utils.debug_msg(self, "new_size: %s" % new_size)
        if new_size == 'custom':
            vol = float(keg_box.children['custom'].children['1'].get_value())
            tare = float(keg_box.children['custom'].children['3'].get_value())
        else:
            vol = utils.keg_data[new_size][0]
            tare = utils.keg_data[new_size][1]

        new_conf = dict()
        new_conf['name'] = keg_box.children['name'].children['val'].get_value()
        new_conf['size'] = new_size
        new_conf['co2'] = keg_box.children['co2_box'].children['1'].get_value()
        new_conf['volume'] = vol
        new_conf['tare'] = tare
        utils.debug_msg(self, "new_conf: %s" % new_conf)
        utils.debug_msg(self, "end")
        return new_conf


    def get_port_data(self, dialog):
        utils.debug_msg(self, "start")
        new_conf = dict()
        new_conf['port'] = dialog.get_field('port_box').children['1'].get_value()
        new_conf['pd_sck'] = dialog.get_field('hx_pins').children['1'].get_value()
        new_conf['dout'] = dialog.get_field('hx_pins').children['3'].get_value()
        new_conf['channel'] = dialog.get_field('channel_box').children['1'].get_value()
        utils.debug_msg(self, "end")
        return new_conf


    def set_keg_gui_data(self, dialog, keg_box_id, new_conf):
        utils.debug_msg(self, "start")
        utils.debug_msg(self, "new_conf: %s" % new_conf)
        utils.debug_msg(self, "keg_box_id: %s" % keg_box_id)
        keg_box = dialog.get_field(keg_box_id)

        keg_box.children['name'].children['val'].set_value(new_conf.get('name', ''))
        keg_box.children['size'].children['val'].set_value(new_conf.get('size', ''))
        keg_box.children['co2_box'].children['1'].set_value(new_conf.get('co2', False))

        if new_conf['size'] == 'custom':
            keg_box.children['custom'].children['1'].set_value(str(new_conf.get('volume', '')))
            keg_box.children['custom'].children['3'].set_value(str(new_conf.get('tare', '')))
        else:
            try:
                pd_sck = utils.keg_data[new_conf['size']][0]
                dout = utils.keg_data[new_conf['size']][1]
            except KeyError:
                pd_sck = ''
                dout = ''
            keg_box.children['custom'].children['1'].set_value(str(pd_sck))
            keg_box.children['custom'].children['3'].set_value(str(dout))
        utils.debug_msg(self, "end")


    def apply_settings(self, widget):
        utils.debug_msg(self, "start")
        self.settings_up = False

        weight_mode = self.settings_dialog.get_field('weight_options').get_value()
        self.api_write('PUT', 'weight_mode', {'weight_mode': weight_mode})
        utils.debug_msg(self, "end")


    def apply_edit_keg(self, widget):
        utils.debug_msg(self, "start")
        self.edit_keg_up = False
        
        self.api_read(force=True)
        hx_list = self.api_data['hx_list']

        port_conf = self.get_port_data(self.edit_keg_dialog)
        port = port_conf['port']
        index = utils.get_index_from_port(port, hx_list)
        channel = port_conf['channel']

        if index != None:
            for attribute in ('pd_sck', 'dout'):
                endpoint = 'hx/%s/%s' % (str(index), attribute)
                self.api_write('PUT', endpoint, {attribute: port_conf[attribute]})

            try:
                chan = hx_list[index]['channels'][channel]
            except KeyError:
                chan = {}
            new_conf = self.get_keg_gui_data(self.edit_keg_dialog, 'keg_box')
            chan['name'] = new_conf['name']
            chan['size'] = new_conf['size']
            chan['volume'] = new_conf['volume']
            chan['tare'] = new_conf['tare']
            chan['co2'] = new_conf['co2']
            endpoint = 'hx/%s/%s/' % (str(index), channel)
            self.api_write('POST', endpoint, chan)
        
        else:
            hx = dict()
            hx['pd_sck'] = port_conf['pd_sck']
            hx['dout'] = port_conf['dout']
            hx['channels'] = dict()
            hx['channels'][channel] = self.get_keg_gui_data(self.edit_keg_dialog, 'keg_box')
            endpoint = 'hx/'
            self.api_write('POST', endpoint, hx)

        self.api_read(force=True)
        utils.debug_msg(self, "end")


    def build_keg_table(self):
        utils.debug_msg(self, "start")
        new_table = gui.Table(width=480)
        new_table.style['margin'] = 'auto'
        new_table.style['text-align'] = 'center'
        new_table.style['padding'] = '2em'

        w_mode = self.api_data.get('weight_mode', 'as_kg_gross')

        # iterate through HX sensors
        for index, hx_conf in enumerate(self.api_data['hx_list']):

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
                    utils.debug_msg(self, hx_conf['channels'][channel])
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

                    table_row = gui.TableRow(height=30)
                    for item in [keg_label, keg_bar, keg_weight]:
                        table_item = gui.TableItem()
                        table_item.append(item)
                        table_row.append(table_item)

                    new_table.append(table_row)

        utils.debug_msg(self, "end")
        return new_table


    def main(self, args):
        self.debug = args["debug"]
        utils.debug_msg(self, "start main")

        self.api_url = "http://127.0.0.1:5000/v1/"
        self.api_data = {}
        self.api_last_updated = 1
        self.api_update_interval = 5
        self.api_read()

        self.settings_up = False
        self.edit_keg_up = False
        self.delete_keg_up = False
        self.co2_list = []

        # root object
        self.container = gui.VBox(width=480)
        self.container.style['margin'] = 'auto'
        self.container.style['text-align'] = 'center'

        # header
        self.header = gui.Table(width=480)
        self.header.style['margin'] = 'auto'
        self.header.style['text-align'] = 'center'
        self.header.style['padding'] = '2em'

        # keg table
        self.keg_table = gui.Table(width=480)
        self.keg_table.style['margin'] = 'auto'
        self.keg_table.style['text-align'] = 'center'
        self.keg_table.style['padding'] = '2em'

        # first row
        first_row = gui.TableRow(height=60)

        # temperature
        t = utils.as_degF(self.api_data.get('temp', 0))
        self.temp = gui.Label("%s<br />CO2:%s%%" % (t, '???'))
        self.temp.style['padding-bottom'] = '1em'
        self.temp.style['white-space'] = 'pre'
        table_item = gui.TableItem(width=100, height=30)
        table_item.append(self.temp)
        first_row.append(table_item)

        # title
        self.title = gui.Label("HOPLITE")
        self.title.style['font-size'] = '2em'
        self.title.style['padding-bottom'] = '0.5em'
        table_item = gui.TableItem(width=240, height=30)
        table_item.append(self.title)
        first_row.append(table_item)

        # settings button
        self.settings_button = gui.Image('/static:settings_16.png', width=16)
        self.settings_button.set_on_click_listener(self.show_settings)
        self.settings_button.style['padding-bottom'] = '1.6em'
        table_item = gui.TableItem(width=100, height=30)
        table_item.append(self.settings_button)
        first_row.append(table_item)

        self.header.append(first_row)
        self.container.append(self.header)

        self.keg_table = self.build_keg_table()

        self.container.append(self.keg_table, 'keg_table')

        try:
            co2 = self.co2_list[0] #TODO: Handle multiple CO2 sources
        except IndexError:
            co2 = "???"
        self.temp.set_text("%s\nCO2:%s%%" % (t, co2))

        utils.debug_msg(self, "end main")

        # return of the root widget
        return self.container


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="HOPLITE: A kegerator monitoring script for RasPi")
    parser.add_argument('--debug',
                    action='store_true',
                    help='Enable debugging messages')
    parsed_args = parser.parse_args()

    userdata_dict = {}
    userdata_dict["debug"] = parsed_args.debug

    start(Web, address="0.0.0.0", port=80,
          standalone=False, update_interval=0.5,
          title='HOPLITE', userdata=(userdata_dict,))
