
from pprint import pprint
from webtest import TestApp
from unittest import TestCase


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


        
        
      