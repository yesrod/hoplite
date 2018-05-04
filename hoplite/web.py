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

    def __init__( self, *args ):
        self.h = Hoplite()

        mem = posix_ipc.SharedMemory('/hoplite', flags=posix_ipc.O_CREAT)
        self.ShMem = mmap.mmap(mem.fd, mem.size)
        mem.close_fd()

        self.ShLock = posix_ipc.Semaphore('/hoplite', flags=posix_ipc.O_CREAT)

        resource_package = __name__
        resource_path = '/static'
        static_path = pkg_resources.resource_filename(resource_package, resource_path)

        super( Web, self ).__init__( *args, static_file_path = static_path )


    def shmem_read(self, timeout=None):
        map_data = ''
        self.ShLock.acquire(timeout)
        self.ShMem.seek(0, 0)
        while True:
                line = self.ShMem.readline()
                if line == '': break
                map_data += line.rstrip('\0')
        self.ShMem.seek(0, 0)
        self.ShLock.release()
        self.ShData = json.loads(map_data)


    def shmem_write(self, timeout=None):
        self.ShLock.acquire(timeout)
        self.shmem_clear()
        self.ShMem.write(json.dumps(self.ShData, indent=2) + '\0')
        self.ShMem.flush()
        self.ShLock.release()


    def shmem_clear(self):
        zero_fill = '\0' * (self.ShMem.size())
        self.ShMem.seek(0, 0)
        self.ShMem.write(zero_fill)
        self.ShMem.seek(0, 0)
        self.ShMem.flush()


    def get_keg_fill_percent( self, w, net_w, tare ):
        max_net_w = net_w * 1000
        keg_tare = tare * 1000
        net_w = max((w - keg_tare), 0)
        fill_percent = net_w / max_net_w
        return fill_percent


    def idle( self ):
        self.shmem_read(5)

        for line in self.KegLines:
            for index, hx_conf in enumerate(self.ShData['config']['hx']):
                # channel A update
                try:
                    w = self.ShData['data']['weight'][index][0]
                    net_w = hx_conf['channels']['A']['size'][0]
                    tare = hx_conf['channels']['A']['size'][1]
                    name = hx_conf['channels']['A']['name']
                    fill_pct = self.get_keg_fill_percent(w, net_w, tare)

                    self.KegLines[index][0][0].set_text(name)
                    self.KegLines[index][0][1].set_size(240 * fill_pct, 30)
                    self.KegLines[index][0][1].style['fill'] = self.h.fill_bar_color(fill_pct)
                    self.KegLines[index][0][2].set_text(self.h.as_kg(w))
                except (KeyError, IndexError):
                    pass

                # channel B update
                try:
                    w = self.ShData['data']['weight'][index][1]
                    net_w = hx_conf['channels']['B']['size'][0]
                    tare = hx_conf['channels']['B']['size'][1]
                    name = hx_conf['channels']['B']['name']
                    fill_pct = self.get_keg_fill_percent(w, net_w, tare)

                    self.KegLines[index][1][0].set_text(name)
                    self.KegLines[index][1][1].set_size(240 * fill_pct, 30)
                    self.KegLines[index][1][1].style['fill'] = self.h.fill_bar_color(fill_pct)
                    self.KegLines[index][1][2].set_text(self.h.as_kg(w))
                except (KeyError, IndexError):
                    pass
        t = self.h.as_degF(self.ShData['data'].get('temp', '0'))
        co2 = self.ShData['data'].get('co2', '???')
        self.temp.set_text("%s<br />CO2:%s%%" % (t, co2))


    def close( self ):
        self.ShMem.close()
        posix_ipc.unlink_shared_memory('/hoplite')
        self.ShLock.release()
        self.ShLock.unlink()

        super( Web, self ).close()


    def show_settings_menu( self, widget ):
        if self.settings_up == True:
            return
        else:
            self.settings_up = True

        self.dialog = gui.GenericDialog(title='Settings', 
                        width='500px')

        for line in self.KegLines:
            for index, hx_conf in enumerate(self.ShData['config']['hx']):

                keg_size_list = self.h.keg_data.keys()
                keg_size_list.append('custom')

                # channel A settings
                try:
                    net_w = hx_conf['channels']['A']['size'][0]
                    tare = hx_conf['channels']['A']['size'][1]
                    name = hx_conf['channels']['A']['name']
                    size_name = hx_conf['channels']['A']['size_name']
                    size = hx_conf['channels']['A']['size']

                    keg_name = gui.TextInput(single_line=True, height='1.5em')
                    keg_name.set_value(name)
                    self.dialog.add_field_with_label(str(index) + 'A_name', 
                                                     'Keg Name', keg_name)

                    keg_size = gui.DropDown.new_from_list(keg_size_list)
                    keg_size.select_by_value(size_name)
                    self.dialog.add_field_with_label(str(index) + 'A_size', 
                                                     'Keg Size', keg_size)

                    custom = gui.HBox( width = 500, height = 30)
                    vol_lbl = gui.Label('Volume (l)')
                    custom.append(vol_lbl, 0)
                    custom_vol = gui.TextInput(single_line=True, 
                                                    width='5em', height='1.5em')
                    custom_vol.set_value(str(size[0]))
                    custom.append( custom_vol, 1 )
                    tare_lbl = gui.Label('Empty Weight (kg)')
                    custom.append( tare_lbl, 2 )
                    custom_tare = gui.TextInput(single_line=True, 
                                                     width='5em', height='1.5em')
                    custom_tare.set_value(str(size[1]))
                    custom.append( custom_tare, 3 )

                    self.dialog.add_field_with_label(str(index) + 'A_custom', 
                                                     'Custom Settings', custom)
                except (KeyError, IndexError):
                    pass

                # channel B settings
                try:
                    net_w = hx_conf['channels']['B']['size'][0]
                    tare = hx_conf['channels']['B']['size'][1]
                    name = hx_conf['channels']['B']['name']
                    size_name = hx_conf['channels']['B']['size_name']
                    size = hx_conf['channels']['B']['size']

                    keg_name = gui.TextInput(single_line=True, height='1.5em')
                    keg_name.set_value(name)
                    self.dialog.add_field_with_label(str(index) + 'B_name',
                                                     'Keg Name', keg_name)

                    keg_size = gui.DropDown.new_from_list(keg_size_list)
                    keg_size.select_by_value(size_name)
                    self.dialog.add_field_with_label(str(index) + 'B_size',
                                                     'Keg Size', keg_size)

                    custom = gui.HBox( width = 500, height = 30)
                    vol_lbl = gui.Label('Volume (l)')
                    custom.append(vol_lbl, 0)
                    custom_vol = gui.TextInput(single_line=True,
                                                    width='5em', height='1.5em')
                    custom_vol.set_value(str(size[0]))
                    custom.append( custom_vol, 1 )
                    tare_lbl = gui.Label('Empty Weight (kg)')
                    custom.append( tare_lbl, 2 )
                    custom_tare = gui.TextInput(single_line=True,
                                                     width='5em', height='1.5em')
                    custom_tare.set_value(str(size[1]))
                    custom.append( custom_tare, 3 )

                    self.dialog.add_field_with_label(str(index) + 'B_custom',
                                                     'Custom Settings', custom)

                except (KeyError, IndexError):
                    pass

        self.dialog.set_on_cancel_dialog_listener( self.cancel_settings )
        self.dialog.set_on_confirm_dialog_listener( self.apply_settings )
        self.dialog.show(self)


    def cancel_settings(self, widget):
        self.settings_up = False


    def apply_settings(self, widget):
        self.settings_up = False

        for index, hx_conf in enumerate(self.ShData['config']['hx']):

            # channel A settings
            try:
                new_name = self.dialog.get_field(str(index) + 'A_name').get_value()
                new_size = self.dialog.get_field(str(index) + 'A_size').get_value()

                if new_size == 'custom':
                    custom = self.dialog.get_field(str(index) + 'A_custom')
                    vol = float(custom.children['1'].get_value())
                    tare = float(custom.children['3'].get_value())
                else:
                    vol = self.h.keg_data[new_size][0]
                    tare = self.h.keg_data[new_size][1]
                hx_conf['channels']['A']['name'] = new_name
                hx_conf['channels']['A']['size_name'] = new_size
                hx_conf['channels']['A']['size'] = [vol, tare]

            except (KeyError, IndexError):
                pass

            # channel B settings
            try:
                new_name = self.dialog.get_field(str(index) + 'B_name').get_value()
                new_size = self.dialog.get_field(str(index) + 'B_size').get_value()
                if new_size == 'custom':
                    custom = self.dialog.get_field(str(index) + 'B_custom')
                    vol = float(custom.children['1'].get_value())
                    tare = float(custom.children['3'].get_value())
                else:
                    vol = self.h.keg_data[new_size][0]
                    tare = self.h.keg_data[new_size][1]
                hx_conf['channels']['B']['name'] = new_name
                hx_conf['channels']['B']['size_name'] = new_size
                hx_conf['channels']['B']['size'] = [vol, tare]

            except (KeyError, IndexError):
                pass

        self.shmem_write(5)


    def main( self ):
        self.shmem_read(5)

        self.KegLines = list()
        self.settings_up = False

        # root object
        self.container = gui.Table(width = 480)
        self.container.style['margin'] = 'auto'
        self.container.style['text-align'] = 'center'
        self.container.style['padding'] = '2em'

        # first row
        first_row = gui.TableRow(height = 60)

        # temperature
        t = self.h.as_degF(self.ShData['data'].get('temp', '0'))
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


        # iterate through HX sensors
        for index, hx_conf in enumerate(self.ShData['config']['hx']):

            hx_weight = self.ShData['data']['weight'][index]
            self.KegLines.insert(index, list())
            self.KegLines[index].insert(0, None)
            self.KegLines[index].insert(1, None)

            # keg A information
            try:
                kegA_name = hx_conf['channels']['A'].get('name', None)
            except KeyError:
                kegA_name = None

            if kegA_name != None:
                kegA_label = gui.Label(kegA_name, width=100, height=30)

                kegA_bar = gui.Svg(240, 30)
                kegA_w = hx_weight[0]
                kegA_net_w = hx_conf['channels']['A']['size'][0]
                kegA_tare = hx_conf['channels']['A']['size'][1]
                kegA_fill_pct = self.get_keg_fill_percent(kegA_w, kegA_net_w, kegA_tare)
                kegA_bar_rect = gui.SvgRectangle(0,0, 240 * kegA_fill_pct,30)
                kegA_bar_rect.style['fill'] = self.h.fill_bar_color(kegA_fill_pct)
                kegA_bar_outline = gui.SvgRectangle(0,0, 240,30)
                kegA_bar_outline.style['fill'] = 'rgb(0,0,0)'
                kegA_bar_outline.style['fill-opacity'] = '0'
                kegA_bar.append(kegA_bar_rect)
                kegA_bar.append(kegA_bar_outline)

                kegA_weight=gui.Label(self.h.as_kg(kegA_w), width=100, height=30)

                try:
                    self.KegLines[index].insert(0, [kegA_label, kegA_bar_rect, kegA_weight])
                except KeyError:
                    self.KegLines.insert(index, [kegA_label, kegA_bar_rect, kegA_weight])

                table_row = gui.TableRow(height=30)
                for item in [kegA_label, kegA_bar, kegA_weight]:
                    table_item = gui.TableItem()
                    table_item.append(item)
                    table_row.append(table_item)

                self.container.append(table_row)


            # keg B information
            try:
                kegB_name = hx_conf['channels']['B'].get('name', None)
            except:
                kegB_name = None

            if kegB_name != None:
                kegB_label = gui.Label(kegB_name, width=100, height=30)

                kegB_bar = gui.Svg(240, 30)
                kegB_w = hx_weight[1]
                kegB_net_w = hx_conf['channels']['B']['size'][0]
                kegB_tare = hx_conf['channels']['B']['size'][1]
                kegB_fill_pct = self.get_keg_fill_percent(kegB_w, kegB_net_w, kegB_tare)
                kegB_bar_rect = gui.SvgRectangle(0,0, 240 * kegB_fill_pct,30)
                kegB_bar_rect.style['fill'] = self.h.fill_bar_color(kegB_fill_pct)
                kegB_bar_outline = gui.SvgRectangle(0,0, 240,30)
                kegB_bar_outline.style['fill'] = 'rgb(0,0,0)'
                kegB_bar_outline.style['fill-opacity'] = '0'
                kegB_bar.append(kegB_bar_rect)
                kegB_bar.append(kegB_bar_outline)

                kegB_weight=gui.Label(self.h.as_kg(kegB_w), width=100, height=30)

                try:
                    self.KegLines[index].insert(1, [kegB_label, kegB_bar_rect, kegB_weight])
                except KeyError:
                    self.KegLines.insert(index, [kegB_label, kegB_bar_rect, kegB_weight])

                table_row = gui.TableRow(height=30)
                for item in [kegB_label, kegB_bar, kegB_weight]:
                    table_item = gui.TableItem()
                    table_item.append(item)
                    table_row.append(table_item)

                self.container.append(table_row)

        # return of the root widget
        return self.container


if __name__ == '__main__':
    start( Web, address="0.0.0.0", port=80, standalone=False, update_interval=0.5 )


