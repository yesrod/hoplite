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
        map_data = ""
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
        self.ShLock.release()


    def shmem_clear(self):
        zero_fill = '\0' * (self.ShMem.size())
        self.ShMem.seek(0, 0)
        self.ShMem.write(zero_fill)
        self.ShMem.seek(0, 0)


    def get_keg_fill_percent( self, keg ):
        keg_data = self.ShData['kegs'][keg].get('size', None)
        if keg_data:
            keg_w = self.ShData['kegs'][keg].get('w', None)
            max_net_w = keg_data[0] * 1000
            keg_tare = keg_data[1] * 1000
            net_w = max((keg_w - keg_tare), 0)
            fill_percent = net_w / max_net_w
        else:
            fill_percent = None
        return fill_percent


    def idle( self ):
        self.shmem_read(5)
        self.kegA_weight.set_text(self.h.as_kg(self.ShData['kegs']['kegA'].get('w', 'No data')))
        self.kegB_weight.set_text(self.h.as_kg(self.ShData['kegs']['kegB'].get('w', 'No data')))
        self.kegA_bar_rect.set_size(280 * self.get_keg_fill_percent('kegA'), 30)
        self.kegB_bar_rect.set_size(280 * self.get_keg_fill_percent('kegB'), 30)


    def close( self ):
        print "Cleaning up shared memory"
        self.ShMem.close()
        posix_ipc.unlink_shared_memory('/hoplite')
        self.ShLock.release()
        self.ShLock.unlink()

        super( hoplite_web, self ).close()


    def main( self ):
        self.shmem_read(5)

        self.container = gui.Widget(width = 480, height = 90 )
        self.container.style['margin'] = 'auto'
        self.container.style['text-align'] = 'center'
        self.container.style['padding'] = '2em'

        self.title = gui.Label( "HOPLITE", width=480, height=30 )
        self.title.style['font-size'] = '2em'
        self.title.style['margin'] = 'auto'
        self.title.style['text-align'] = 'center'
        self.title.style['padding-bottom'] = '1em'

        self.kegA = gui.HBox( width = 480, height = 30)

        self.kegA_label = gui.Label( self.ShData['kegs']['kegA'].get('name', 'No name'), width=100, height=30 )
        self.kegA_label.style['margin'] = 'auto'
        self.kegA_label.style['float'] = 'left'

        self.kegA_bar = gui.Svg( 280, 30 )

        self.kegA_bar_rect = gui.SvgRectangle( 0, 0, 280 * self.get_keg_fill_percent('kegA'), 30 )
        self.kegA_bar_rect.style['fill'] = 'rgb(255,0,0)'

        self.kegA_bar_outline = gui.SvgRectangle( 0, 0, 280, 30 )
        self.kegA_bar_outline.style['fill'] = 'rgb(0,0,0)'
        self.kegA_bar_outline.style['fill-opacity'] = '0'

        self.kegA_bar.append( self.kegA_bar_rect )
        self.kegA_bar.append( self.kegA_bar_outline )

        self.kegA_weight = gui.Label( self.h.as_kg(self.ShData['kegs']['kegA'].get('w', 'No data')), width=100, height=30 )
        self.kegA_weight.style['margin'] = 'auto'
        self.kegA_weight.style['float'] = 'right'

        self.kegA.append( self.kegA_label, 1 )
        self.kegA.append( self.kegA_bar, 2 )
        self.kegA.append( self.kegA_weight, 3 )

        self.kegB = gui.HBox( width = 480, height = 30)

        self.kegB_label = gui.Label( self.ShData['kegs']['kegB'].get('name', 'No name'), width=100, height=30 )
        self.kegB_label.style['margin'] = 'auto'
        self.kegB_label.style['float'] = 'left'

        self.kegB_bar = gui.Svg( 280, 30 )

        self.kegB_bar_rect = gui.SvgRectangle( 0, 0, 280 * self.get_keg_fill_percent('kegB'), 30 )
        self.kegB_bar_rect.style['fill'] = 'rgb(255,0,0)'

        self.kegB_bar_outline = gui.SvgRectangle( 0, 0, 280, 30 )
        self.kegB_bar_outline.style['fill'] = 'rgb(0,0,0)'
        self.kegB_bar_outline.style['fill-opacity'] = '0'

        self.kegB_bar.append( self.kegB_bar_rect )
        self.kegB_bar.append( self.kegB_bar_outline )

        self.kegB_weight = gui.Label( self.h.as_kg(self.ShData['kegs']['kegB'].get('w', 'No data')), width=100, height=30 )
        self.kegB_weight.style['margin'] = 'auto'
        self.kegB_weight.style['float'] = 'right'

        self.kegB.append( self.kegB_label, 1 )
        self.kegB.append( self.kegB_bar, 2 )
        self.kegB.append( self.kegB_weight, 3 )

        self.container.append( self.title )
        self.container.append( self.kegA )
        self.container.append( self.kegB )

        #return of the root widget
        return self.container


if __name__ == '__main__':
    start( hoplite_web, address="192.168.1.173", standalone=False )


