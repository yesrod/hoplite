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


    def get_keg_fill_percent( self, keg ):
        keg_data = self.ShData['config']['kegs'][keg].get('size', None)
        if keg_data:
            keg_w = self.ShData['data'].get(keg + '_w', None)
            if keg_w:
                max_net_w = keg_data[0] * 1000
                keg_tare = keg_data[1] * 1000
                net_w = max((keg_w - keg_tare), 0)
                fill_percent = net_w / max_net_w
            else:
                fill_percent = 0
        else:
            fill_percent = 0
        return fill_percent


    def idle( self ):
        self.shmem_read(5)
        self.kegA_label.set_text(self.ShData['config']['kegs']['kegA'].get('name', 'No name'))
        self.kegB_label.set_text(self.ShData['config']['kegs']['kegB'].get('name', 'No name'))
        self.kegA_weight.set_text(self.h.as_kg(self.ShData['data'].get('kegA_w', 0)))
        self.kegB_weight.set_text(self.h.as_kg(self.ShData['data'].get('kegB_w', 0)))
        self.kegA_bar_rect.set_size(280 * self.get_keg_fill_percent('kegA'), 30)
        self.kegB_bar_rect.set_size(280 * self.get_keg_fill_percent('kegB'), 30)
        self.temp.set_text(self.h.as_degF(self.ShData['data'].get('temp', 'No data')))


    def close( self ):
        self.ShMem.close()
        posix_ipc.unlink_shared_memory('/hoplite')
        self.ShLock.release()
        self.ShLock.unlink()

        super( Web, self ).close()


    def show_settings_menu( self, widget ):
        self.dialog = gui.GenericDialog(title='Settings', 
                        width='500px')

        kegA_name = gui.TextInput(single_line=True, height='1.5em')
        kegA_name.set_value(self.ShData['config']['kegs']['kegA']['name'])
        self.dialog.add_field_with_label('kegA_name', 'Left Keg', kegA_name)

        keg_size_list = self.h.keg_data.keys()
        keg_size_list.append('custom')

        kegA_size = gui.DropDown.new_from_list(keg_size_list)
        kegA_size.select_by_value(self.ShData['config']['kegs']['kegA']['size_name'])        
        self.dialog.add_field_with_label('kegA_size', 'Keg Size', kegA_size)

        kegA_custom = gui.HBox( width = 500, height = 30)

        kegA_vol_lbl = gui.Label('Volume (l)')
        kegA_custom.append( kegA_vol_lbl, 0 )

        kegA_custom_vol = gui.TextInput(single_line=True, width='5em', height='1.5em')
        kegA_custom_vol.set_value(str(self.ShData['config']['kegs']['kegA']['size'][0]))
        kegA_custom.append( kegA_custom_vol, 1 )

        kegA_tare_lbl = gui.Label('Empty Weight (kg)')
        kegA_custom.append( kegA_tare_lbl, 2 )

        kegA_custom_tare = gui.TextInput(single_line=True, width='5em', height='1.5em')
        kegA_custom_tare.set_value(str(self.ShData['config']['kegs']['kegA']['size'][1]))
        kegA_custom.append( kegA_custom_tare, 3 )

        self.dialog.add_field_with_label('kegA_custom', 'Custom Settings', kegA_custom)

        kegB_name = gui.TextInput(single_line=True, height='1.5em')
        kegB_name.set_value(self.ShData['config']['kegs']['kegB']['name'])
        self.dialog.add_field_with_label('kegB_name', 'Right Keg', kegB_name)

        kegB_size = gui.DropDown.new_from_list(keg_size_list)
        kegB_size.select_by_value(self.ShData['config']['kegs']['kegB']['size_name'])
        self.dialog.add_field_with_label('kegB_size', 'Keg Size', kegB_size)

        kegB_custom = gui.HBox( width = 500, height = 30)

        kegB_vol_lbl = gui.Label('Volume (l)')
        kegB_custom.append( kegB_vol_lbl, 0 )

        kegB_custom_vol = gui.TextInput(single_line=True, width='5em', height='1.5em')
        kegB_custom_vol.set_value(str(self.ShData['config']['kegs']['kegB']['size'][0]))
        kegB_custom.append( kegB_custom_vol, 1 )

        kegB_tare_lbl = gui.Label('Empty Weight (kg)')
        kegB_custom.append( kegB_tare_lbl, 2 )

        kegB_custom_tare = gui.TextInput(single_line=True, width='5em', height='1.5em')
        kegB_custom_tare.set_value(str(self.ShData['config']['kegs']['kegB']['size'][1]))
        kegB_custom.append( kegB_custom_tare, 3 )

        self.dialog.add_field_with_label('kegB_custom', 'Custom Settings', kegB_custom)

        self.dialog.set_on_confirm_dialog_listener( self.apply_settings )
        self.dialog.show(self)


    def apply_settings( self, widget ):
        kegA_new_name = self.dialog.get_field('kegA_name').get_value()
        self.ShData['config']['kegs']['kegA']['name'] = kegA_new_name

        kegA_new_size = self.dialog.get_field('kegA_size').get_value()
        self.ShData['config']['kegs']['kegA']['size_name'] = kegA_new_size
        if kegA_new_size == 'custom':
            vol = float(self.dialog.get_field('kegA_custom_vol').get_value())
            tare = float(self.dialog.get_field('kegA_custom_tare').get_value())
            self.ShData['config']['kegs']['kegA']['size'] = [vol, tare]
        else:
            self.ShData['config']['kegs']['kegA']['size'] = self.h.keg_data[kegA_new_size]

        kegB_new_name = self.dialog.get_field('kegB_name').get_value()
        self.ShData['config']['kegs']['kegB']['name'] = kegB_new_name

        kegB_new_size = self.dialog.get_field('kegB_size').get_value()
        self.ShData['config']['kegs']['kegB']['size_name'] = kegB_new_size

        if kegB_new_size == 'custom':
            vol = float(self.dialog.get_field('kegB_custom_vol').get_value())
            tare = float(self.dialog.get_field('kegB_custom_tare').get_value())
            self.ShData['config']['kegs']['kegB']['size'] = [vol, tare]
        else:
            self.ShData['config']['kegs']['kegB']['size'] = self.h.keg_data[kegB_new_size]

        self.shmem_write(5)



    def main( self ):
        self.shmem_read(5)

        # root object
        self.container = gui.HBox(width = 480, height = 150 )
        self.container.style['margin'] = 'auto'
        self.container.style['text-align'] = 'center'
        self.container.style['padding'] = '2em'

        # VBoxes for vertical alignment
        left = gui.VBox(height = 150)
        center = gui.VBox(height = 150)
        right = gui.VBox(height = 150)

        self.container.append(left, 1)
        self.container.append(center, 2)
        self.container.append(right, 3)

        # temperature
        self.temp = gui.Label(self.h.as_degF(self.ShData['data'].get('temp', 'No data')))
        self.temp.style['padding-bottom'] = '1em'
        left.append(self.temp, 1)

        # settings button
        self.settings_button = gui.Image('/res/settings_16.png')
        self.settings_button.set_on_click_listener(self.show_settings_menu)
        self.settings_button.style['padding-bottom'] = '1.6em'
        right.append(self.settings_button, 1)

        # title
        self.title = gui.Label("HOPLITE")
        self.title.style['font-size'] = '2em'
        self.title.style['padding-bottom'] = '0.5em'
        center.append(self.title, 1)

        # keg A information
        self.kegA_label = gui.Label(self.ShData['config']['kegs']['kegA'].get('name', 'No name'),
                                     width=100, height=30)
        left.append(self.kegA_label, 2)

        self.kegA_bar = gui.Svg( 240, 30 )

        self.kegA_bar_rect = gui.SvgRectangle( 0, 0, 
                                               240 * self.get_keg_fill_percent('kegA'), 30 )
        self.kegA_bar_rect.style['fill'] = 'rgb(255,0,0)'

        self.kegA_bar_outline = gui.SvgRectangle( 0, 0, 240, 30 )
        self.kegA_bar_outline.style['fill'] = 'rgb(0,0,0)'
        self.kegA_bar_outline.style['fill-opacity'] = '0'

        self.kegA_bar.append( self.kegA_bar_rect )
        self.kegA_bar.append( self.kegA_bar_outline )
        center.append(self.kegA_bar, 2)

        self.kegA_weight=gui.Label(self.h.as_kg(self.ShData['data'].get('kegA_w', 0)),
                                                width=100, height=30 )

        right.append( self.kegA_weight, 2 )

        # keg B information

        self.kegB_label = gui.Label(self.ShData['config']['kegs']['kegB'].get('name', 'No name'),
                                     width=100, height=30 )
        left.append(self.kegB_label, 3)

        self.kegB_bar = gui.Svg( 240, 30 )
        self.kegB_bar_rect = gui.SvgRectangle( 0, 0, 
                                               240 * self.get_keg_fill_percent('kegB'), 30 )
        self.kegB_bar_rect.style['fill'] = 'rgb(255,0,0)'
        self.kegB_bar_outline = gui.SvgRectangle( 0, 0, 240, 30 )
        self.kegB_bar_outline.style['fill'] = 'rgb(0,0,0)'
        self.kegB_bar_outline.style['fill-opacity'] = '0'

        self.kegB_bar.append( self.kegB_bar_rect )
        self.kegB_bar.append( self.kegB_bar_outline )
        center.append(self.kegB_bar, 3)

        self.kegB_weight=gui.Label(self.h.as_kg(self.ShData['data'].get('kegB_w', 0)),
                                   width=100, height=30 )
        right.append(self.kegB_weight, 3)

        # return of the root widget
        return self.container


if __name__ == '__main__':
    start( Web, address="192.168.1.173", standalone=False )


