import remi.gui as gui
from remi import start, App

import sys
import time
import json
import mmap
import posix_ipc
import pkg_resources

from . import Hoplite


class Web(App):

    global h

    global ShMem
    global ShLock
    global ShData

    global KegLines

    global settings_up

    def __init__(self, *args):
        self.h = Hoplite()

        mem = posix_ipc.SharedMemory('/hoplite', flags=posix_ipc.O_CREAT)
        self.ShMem = mmap.mmap(mem.fd, mem.size)
        mem.close_fd()

        self.ShLock = posix_ipc.Semaphore('/hoplite', flags=posix_ipc.O_CREAT)

        resource_package = __name__
        resource_path = '/static'
        static_path = pkg_resources.resource_filename(
            resource_package, resource_path)

        super(Web, self).__init__(*args, static_file_path=static_path)


    def shmem_read(self, timeout=None):
        map_data = b''
        self.ShLock.acquire(timeout)
        self.ShMem.seek(0, 0)
        while True:
                line = self.ShMem.readline()
                if line == b'':
                    break
                map_data += line.rstrip(b'\0')
        self.ShMem.seek(0, 0)
        self.ShLock.release()
        self.ShData = json.loads(map_data.decode())


    def shmem_write(self, timeout=None):
        self.ShLock.acquire(timeout)
        self.shmem_clear()
        self.ShMem.write(json.dumps(self.ShData, indent=2).encode())
        self.ShMem.flush()
        self.ShLock.release()


    def shmem_clear(self):
        zero_fill = b'\0' * (self.ShMem.size())
        self.ShMem.seek(0, 0)
        self.ShMem.write(zero_fill)
        self.ShMem.seek(0, 0)
        self.ShMem.flush()


    def get_keg_fill_percent(self, w, cap, tare):
        keg_cap = cap * 1000
        keg_tare = tare * 1000
        net_w = max((w - keg_tare), 0)
        fill_percent = net_w / keg_cap
        return fill_percent


    def idle(self):
        self.shmem_read(5)

        w_mode = self.ShData['config'].get('weight_mode', 'as_kg_gross')

        for line in self.KegLines:
            for index, hx_conf in enumerate(self.ShData['config']['hx']):
                for subindex, channel in enumerate(['A', 'B']):
                    # channel update
                    try:
                        w = self.ShData['data']['weight'][index][subindex]
                        cap = hx_conf['channels'][channel]['size'][0]
                        tare = hx_conf['channels'][channel]['size'][1]
                        name = hx_conf['channels'][channel]['name']
                        fill_pct = self.get_keg_fill_percent(w, cap, tare)

                        self.KegLines[index][subindex][0].set_text(name)
                        self.KegLines[index][subindex][
                            1].set_size(240 * fill_pct, 30)
                        self.KegLines[index][subindex][1].style[
                            'fill'] = self.h.fill_bar_color(fill_pct)
                        self.KegLines[index][subindex][2].set_text(self.h.format_weight(
                            w, (tare * 1000),  mode=w_mode, cap=(cap * 1000)))
                    except (KeyError, IndexError):
                        pass

        t = self.h.as_degF(self.ShData['data'].get('temp', 0))
        co2 = self.ShData['data'].get('co2', '???')
        self.temp.set_text("%s<br />CO2:%s%%" % (t, co2))


    def close(self):
        self.ShMem.close()
        posix_ipc.unlink_shared_memory('/hoplite')
        self.ShLock.release()
        self.ShLock.unlink()

        super(Web, self).close()


    def build_keg_settings(self, hx_conf, index, channel):
        cap = hx_conf['channels'][channel]['size'][0]
        tare = hx_conf['channels'][channel]['size'][1]
        name = hx_conf['channels'][channel]['name']
        size_name = hx_conf['channels'][channel]['size_name']
        size = hx_conf['channels'][channel]['size']

        keg_size_list = list(self.h.keg_data)
        keg_size_list.append('custom')

        keg_box = gui.Widget()

        box_name = gui.Label('Sensor ' + str(index) + ' Channel ' + channel)
        keg_box.append(box_name)

        keg_name = gui.HBox()
        keg_name_lbl = gui.Label('Keg Name', width='20%')
        keg_name.append(keg_name_lbl, 'lbl')
        keg_name_val = gui.TextInput(single_line=True, height='1.5em')
        keg_name_val.set_value(name)
        keg_name.append(keg_name_val, 'val')
        keg_box.append(keg_name, 'name')

        keg_size = gui.HBox()
        keg_size_lbl = gui.Label('Keg Size', width='20%')
        keg_size.append(keg_size_lbl, 'lbl')
        keg_size_val = gui.DropDown.new_from_list(keg_size_list)
        keg_size_val.select_by_value(size_name)
        keg_size.append(keg_size_val, 'val')
        keg_box.append(keg_size, 'size')

        custom = gui.HBox()
        vol_lbl = gui.Label('Volume (l)', width='20%')
        custom.append(vol_lbl, 0)
        custom_vol = gui.TextInput(
            single_line=True, height='1.5em', width='30%')
        custom_vol.set_value(str(size[0]))
        custom.append(custom_vol, 1)
        tare_lbl = gui.Label('Empty Weight (kg)', width='30%')
        custom.append(tare_lbl, 2)
        custom_tare = gui.TextInput(
            single_line=True, height='1.5em', width='20%')
        custom_tare.set_value(str(size[1]))
        custom.append(custom_tare, 3)

        keg_box.append(custom, 'custom')

        return keg_box


    def show_settings_menu(self, widget):
        if self.settings_up == True:
            return
        else:
            self.settings_up = True

        self.dialog = gui.GenericDialog(title='Settings',
                                        width='500px')

        # weight display options
        weight_options_list = ['as_kg_gross', 'as_kg_net', 'as_pint', 'as_pct']
        weight_options = gui.DropDown.new_from_list(weight_options_list)
        weight_options.select_by_value(self.ShData['config']['weight_mode'])
        self.dialog.add_field_with_label(
            'weight_options', 'Display Keg Weight', weight_options)

        for line in self.KegLines:
            for index, hx_conf in enumerate(self.ShData['config']['hx']):

                # channel A settings
                try:
                    keg_box = self.build_keg_settings(hx_conf, index, 'A')
                    self.dialog.add_field(str(index) + 'A_box', keg_box)

                except (KeyError, IndexError):
                    pass

                # channel B settings
                try:
                    keg_box = self.build_keg_settings(hx_conf, index, 'B')
                    self.dialog.add_field(str(index) + 'B_box', keg_box)

                except (KeyError, IndexError):
                    pass

        self.dialog.set_on_cancel_dialog_listener(self.cancel_settings)
        self.dialog.set_on_confirm_dialog_listener(self.apply_settings)
        self.dialog.show(self)


    def cancel_settings(self, widget):
        self.settings_up = False


    def get_keg_settings(self, hx_conf, index, channel):
        keg_box = self.dialog.get_field(str(index) + channel + '_box')

        new_name = keg_box.children['name'].children['val'].get_value()
        new_size = keg_box.children['size'].children['val'].get_value()

        if new_size == 'custom':
            custom = keg_box.children['custom']
            vol = float(custom.children['1'].get_value())
            tare = float(custom.children['3'].get_value())
        else:
            vol = self.h.keg_data[new_size][0]
            tare = self.h.keg_data[new_size][1]
        hx_conf['channels'][channel]['name'] = new_name
        hx_conf['channels'][channel]['size_name'] = new_size
        hx_conf['channels'][channel]['size'] = [vol, tare]


    def apply_settings(self, widget):
        self.settings_up = False

        weight_mode = self.dialog.get_field('weight_options').get_value()
        self.ShData['config']['weight_mode'] = weight_mode

        for index, hx_conf in enumerate(self.ShData['config']['hx']):

            # channel A settings
            try:
                self.get_keg_settings(hx_conf, index, 'A')

            except (KeyError, IndexError):
                pass

            # channel B settings
            try:
                self.get_keg_settings(hx_conf, index, 'B')

            except (KeyError, IndexError):
                pass

        self.shmem_write(5)


    def main(self):
        self.shmem_read(5)

        self.KegLines = list()
        self.settings_up = False

        # root object
        self.container = gui.Table(width=480)
        self.container.style['margin'] = 'auto'
        self.container.style['text-align'] = 'center'
        self.container.style['padding'] = '2em'

        # first row
        first_row = gui.TableRow(height=60)

        # temperature
        t = self.h.as_degF(self.ShData['data'].get('temp', 0))
        co2 = self.ShData['data'].get('co2', '???')
        self.temp = gui.Label("%s<br />CO2:%s%%" % (t, co2))
        self.temp.style['padding-bottom'] = '1em'
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
        self.settings_button = gui.Image('/res/settings_16.png', width=16)
        self.settings_button.set_on_click_listener(self.show_settings_menu)
        self.settings_button.style['padding-bottom'] = '1.6em'
        table_item = gui.TableItem()
        table_item.append(self.settings_button)
        first_row.append(table_item)

        self.container.append(first_row)

        w_mode = self.ShData['config'].get('weight_mode', 'as_kg_gross')

        # iterate through HX sensors
        for index, hx_conf in enumerate(self.ShData['config']['hx']):

            hx_weight = self.ShData['data']['weight'][index]
            self.KegLines.insert(index, list())
            self.KegLines[index].insert(0, None)
            self.KegLines[index].insert(1, None)

            # keg information
            for subindex, channel in enumerate(['A', 'B']):
                try:
                    keg_name = hx_conf['channels'][channel].get('name', None)
                except KeyError:
                    keg_name = None

                if keg_name != None:
                    keg_label = gui.Label(keg_name, width=100, height=30)

                    keg_bar = gui.Svg(240, 30)
                    keg_w = hx_weight[subindex]
                    keg_cap = hx_conf['channels'][channel]['size'][0]
                    keg_tare = hx_conf['channels'][channel]['size'][1]
                    keg_fill_pct = self.get_keg_fill_percent(
                        keg_w, keg_cap, keg_tare)
                    keg_bar_rect = gui.SvgRectangle(0, 0, 240 * keg_fill_pct, 30)
                    keg_bar_rect.style[
                        'fill'] = self.h.fill_bar_color(keg_fill_pct)
                    keg_bar_outline = gui.SvgRectangle(0, 0, 240, 30)
                    keg_bar_outline.style['fill'] = 'rgb(0,0,0)'
                    keg_bar_outline.style['fill-opacity'] = '0'
                    keg_bar.append(keg_bar_rect)
                    keg_bar.append(keg_bar_outline)

                    keg_weight = gui.Label(self.h.format_weight(
                        keg_w, (keg_tare * 1000), mode=w_mode, cap=(keg_cap * 1000)), 
                        width=100, height=30)

                    try:
                        self.KegLines[index].insert(
                            subindex, [keg_label, keg_bar_rect, keg_weight])
                    except KeyError:
                        self.KegLines.insert(
                            index, [keg_label, keg_bar_rect, keg_weight])

                    table_row = gui.TableRow(height=30)
                    for item in [keg_label, keg_bar, keg_weight]:
                        table_item = gui.TableItem()
                        table_item.append(item)
                        table_row.append(table_item)

                    self.container.append(table_row)

        # return of the root widget
        return self.container


if __name__ == '__main__':
    start(Web, address="0.0.0.0", port=80,
          standalone=False, update_interval=0.5)
