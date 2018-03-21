import remi.gui as gui
from remi import start, App

import sys
import time

from hoplite import hoplite

class hoplite_web(App):

    global h

    def __init__( self, *args ):
        self.h = hoplite()
        super( hoplite_web, self ).__init__( *args )

    def main( self ):
        self.h.read_weight()
        container = gui.VBox(width = 120, height = 100)
        kegA_label = gui.Label( self.h.as_kg(self.h.kegA), width=100, height=30 )
        kegB_label = gui.Label( self.h.as_kg(self.h.kegB), width=100, height=30 )
        
        container.append( kegA_label )
        container.append( kegB_label )

        #return of the root widget
        return container


start( hoplite_web, address="192.168.1.173" )
