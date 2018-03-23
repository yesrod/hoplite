import remi.gui as gui
from remi import start, App

import sys
import time
import json
import mmap
import posix_ipc

from hoplite import Hoplite

class hoplite_web(App):

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

        super( hoplite_web, self ).__init__( *args )


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


    def close( self ):
        self.ShMem.close()
        posix_ipc.unlink_shared_memory('/hoplite')
        self.ShLock.release()
        self.ShLock.unlink()

        super( hoplite_web, self ).close()


    def show_settings_menu( self, widget ):
        self.dialog = gui.GenericDialog(title='Settings', 
                        message='Settings go here! Eventually!', 
                        width='500px')

        kegA_name = gui.TextInput(single_line=True)
        kegA_name.set_value(self.ShData['config']['kegs']['kegA']['name'])
        self.dialog.add_field_with_label('kegA_name', 'Left Keg', kegA_name)

        kegB_name = gui.TextInput(single_line=True)
        kegB_name.set_value(self.ShData['config']['kegs']['kegB']['name'])
        self.dialog.add_field_with_label('kegB_name', 'Right Keg', kegB_name)

        self.dialog.set_on_confirm_dialog_listener( self.apply_settings )
        self.dialog.show(self)


    def apply_settings( self, widget ):
        print "apply settings"
        kegA_new_name = self.dialog.get_field('kegA_name').get_value()
        self.ShData['config']['kegs']['kegA']['name'] = kegA_new_name

        kegB_new_name = self.dialog.get_field('kegB_name').get_value()
        self.ShData['config']['kegs']['kegB']['name'] = kegB_new_name

        self.shmem_write(5)



    def main( self ):
        self.shmem_read(5)

        # root object
        self.container = gui.Widget(width = 480, height = 90 )
        self.container.style['margin'] = 'auto'
        self.container.style['text-align'] = 'center'
        self.container.style['padding'] = '2em'

        # settings button
        self.settings_button = gui.Button("Settings")
        self.settings_button.style['float'] = 'right'
        self.settings_button.set_on_click_listener(self.show_settings_menu)

        # title
        self.title = gui.Label( "HOPLITE", width=480, height=30 )
        self.title.style['font-size'] = '2em'
        self.title.style['margin'] = 'auto'
        self.title.style['text-align'] = 'center'
        self.title.style['padding-bottom'] = '1em'

        # keg A information
        self.kegA = gui.HBox( width = 480, height = 30)

        self.kegA_label = gui.Label(self.ShData['config']['kegs']['kegA'].get('name', 'No name'),
                                     width=100, height=30)
        self.kegA_label.style['margin'] = 'auto'
        self.kegA_label.style['float'] = 'left'

        self.kegA_bar = gui.Svg( 280, 30 )

        self.kegA_bar_rect = gui.SvgRectangle( 0, 0, 
                                               280 * self.get_keg_fill_percent('kegA'), 30 )
        self.kegA_bar_rect.style['fill'] = 'rgb(255,0,0)'

        self.kegA_bar_outline = gui.SvgRectangle( 0, 0, 280, 30 )
        self.kegA_bar_outline.style['fill'] = 'rgb(0,0,0)'
        self.kegA_bar_outline.style['fill-opacity'] = '0'

        self.kegA_bar.append( self.kegA_bar_rect )
        self.kegA_bar.append( self.kegA_bar_outline )

        self.kegA_weight=gui.Label(self.h.as_kg(self.ShData['data'].get('kegA_w', 0)),
                                                width=100, height=30 )
        self.kegA_weight.style['margin'] = 'auto'
        self.kegA_weight.style['float'] = 'right'

        self.kegA.append( self.kegA_label, 1 )
        self.kegA.append( self.kegA_bar, 2 )
        self.kegA.append( self.kegA_weight, 3 )

        # keg B information
        self.kegB = gui.HBox( width = 480, height = 30)

        self.kegB_label = gui.Label(self.ShData['config']['kegs']['kegB'].get('name', 'No name'),
                                     width=100, height=30 )
        self.kegB_label.style['margin'] = 'auto'
        self.kegB_label.style['float'] = 'left'

        self.kegB_bar = gui.Svg( 280, 30 )

        self.kegB_bar_rect = gui.SvgRectangle( 0, 0, 
                                               280 * self.get_keg_fill_percent('kegB'), 30 )
        self.kegB_bar_rect.style['fill'] = 'rgb(255,0,0)'

        self.kegB_bar_outline = gui.SvgRectangle( 0, 0, 280, 30 )
        self.kegB_bar_outline.style['fill'] = 'rgb(0,0,0)'
        self.kegB_bar_outline.style['fill-opacity'] = '0'

        self.kegB_bar.append( self.kegB_bar_rect )
        self.kegB_bar.append( self.kegB_bar_outline )

        self.kegB_weight=gui.Label(self.h.as_kg(self.ShData['data'].get('kegB_w', 0)),
                                   width=100, height=30 )
        self.kegB_weight.style['margin'] = 'auto'
        self.kegB_weight.style['float'] = 'right'

        self.kegB.append( self.kegB_label, 1 )
        self.kegB.append( self.kegB_bar, 2 )
        self.kegB.append( self.kegB_weight, 3 )

        # attach everything to container
        self.container.append( self.settings_button )
        self.container.append( self.title )
        self.container.append( self.kegA )
        self.container.append( self.kegB )

        # return of the root widget
        return self.container


if __name__ == '__main__':
    start( hoplite_web, address="192.168.1.173", standalone=False )


