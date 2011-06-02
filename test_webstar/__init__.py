
import types
from pprint import pprint
import sys

from webtest import TestApp
import unittest
from webob.dec import wsgify as as_request
from webob.response import Response

class TestCase(unittest.TestCase):
    
    def autostart(self, environ, start):
        start('200 OK', [('Content-Type', 'text-plain')])


class EchoApp(object):
    
    """Simple app for route testing.
    
    Just echos out a string given at construnction time.
    
    """
    
    def __init__(self, output=None, start=True):
        self.start = start
        self.output = output
    
    def __call__(self, environ, start):
        if self.start:
            start('200 OK', [('Content-Type', 'text/plain')])
        return [str(self.output)]
    
    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.output)


class DummyModule(types.ModuleType):
    
    def __init__(self, name):
        super(DummyModule, self).__init__(name)
        self.name = name
        sys.modules[name] = self
        self.__file__ = __file__
    
    def remove(self):
        del sys.modules[self.__name__]
    
    @classmethod
    def remove_all(self):
        for module in sys.modules.values():
            if isinstance(module, DummyModule):
                module.remove()
    
    def __call__(self, name):
        self.__path__ = ['<fake>']
        return self.__class__(self.name + '.' + name)
    
    def __repr__(self):
        return '<DummyModule %s>' % name



        
        
      