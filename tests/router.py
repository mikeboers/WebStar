  
from . import *
from webstar.core import *
from webstar import core
from webstar.router import Router
from webstar.pattern import FormatMatchError

class TestRouterBasics(TestCase):
    
    def autostart(self, environ, start):
        start('200 OK', [('Content-Type', 'text-plain')])
    
    def setUp(self):
        self.router = Router()
        self.app = TestApp(self.router)
        
        @self.router.register('/static')
        def static(environ, start):
            self.autostart(environ, start)
            return ['static response']
        
        @self.router.register('/{fruit:apple|banana}')
        def fruit(environ, start):
            self.autostart(environ, start)
            return ['fruit']
        
        @self.router.register('/{num:\d+}', _parsers=dict(num=int))
        def numbers(environ, start):
            self.autostart(environ, start)
            return ['number-%d' % get_route_data(environ)['num']]
    
    def test_miss(self):
        res = self.app.get('/notfound', status=404)
        self.assertEqual(res.status, '404 Not Found')
        
    def test_static(self):
        res = self.app.get('/static')
        self.assertEqual(res.body, 'static response')
    
    def test_basic_re(self):
        res = self.app.get('/apple')
        self.assertEqual(res.body, 'fruit')
        res = self.app.get('/banana')
        self.assertEqual(res.body, 'fruit')
    
    def test_number_re(self):
        res = self.app.get('/1234')
        self.assertEqual(res.body, 'number-1234')
    
    def test_number_gen(self):
        path = self.router.url_for(num=314)
        self.assertEqual('/314', path)
    
    def test_gen_mismatch(self):
        path = self.router.url_for(fruit='apple')
        self.assertEqual(path, '/apple')
        self.assertRaises(FormatMatchError, self.router.url_for, fruit='carrot')

