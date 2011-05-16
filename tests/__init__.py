
import types
from pprint import pprint
import sys

from webtest import TestApp
import unittest


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



def _assert_next_history_step(res, **kwargs):
    environ_key = 'webstar.test.history_step_i'
    environ = res.environ
    # Notice that we are skipping the first one here
    i = environ[environ_key] = environ.get(environ_key, 0) + 1
    chunk = History.from_environ(environ)[i]

    data = kwargs.pop('_data', None)

    for k, v in kwargs.items():
        v2 = getattr(chunk, k, None)
        assert v == v2, 'on key %r: %r (expected) != %r (actual)' % (k, v, v2)

    if data is not None:
        assert dict(chunk.data) == data, '%r != %r' % (dict(chunk.data), data)


        
        
      