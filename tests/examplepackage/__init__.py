
from .. import *

def autostart(environ, start):
    start('200 OK', [('Content-Type', 'text-plain')])
    
def __app__(environ, start):
    autostart(environ, start)
    return ['package.__init__']