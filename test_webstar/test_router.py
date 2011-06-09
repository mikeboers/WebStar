  
from . import *
from webstar.core import *
from webstar import core
from webstar.router import Router

class TestRouterBasics(TestCase):
    
    def setUp(self):
        self.router = Router()
        self.app = TestApp(self.router)
        
        @self.router.register('/static')
        def static(environ, start):
            self.autostart(environ, start)
            return ['static; path_info=%(PATH_INFO)r, script_name=%(SCRIPT_NAME)r' % environ]
        
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
        self.assertEqual(res.body, "static; path_info='/', script_name='/static'")
    
    def test_static_incomplete(self):
        res = self.app.get('/static/more')
        self.assertEqual(res.body, "static; path_info='/more', script_name='/static'")
    
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
        self.assertRaises(GenerationError, self.router.url_for, fruit='carrot')


class TestDummyModules(TestCase):
    
    def setUp(self):
        root = self.root = DummyModule('dummy')
        root.__app__ = EchoApp('/dummy')
        a = root('a')
        a.__app__ = EchoApp('/dummy/A')
        b = root('b')
        b.__app__ = EchoApp('/dummy/B')
        leaf = b('leaf')
        leaf.__app__ = EchoApp('/dummy/B/leaf')
        
    def tearDown(self):
        DummyModule.remove_all()
    
    def test_basic(self):
        router = Router()
        router.register_package(None, self.root, testing=True, include_self=True)
        self.app = TestApp(router)
        
        res = self.app.get('/')
        self.assertEqual(res.body, '/dummy')
        res = self.app.get('/a')
        self.assertEqual(res.body, '/dummy/A')
        res = self.app.get('/b')
        self.assertEqual(res.body, '/dummy/B')
        res = self.app.get('/b/leaf')
        self.assertEqual(res.body, '/dummy/B')
        
    def test_recursive(self):
        router = Router()
        router.register_package(None, self.root, recursive=True, testing=True, include_self=True)
        router.print_graph()
        self.app = TestApp(router)

        res = self.app.get('/')
        self.assertEqual(res.body, '/dummy')
        res = self.app.get('/a')
        self.assertEqual(res.body, '/dummy/A')
        res = self.app.get('/b')
        self.assertEqual(res.body, '/dummy/B')
        res = self.app.get('/b/leaf')
        self.assertEqual(res.body, '/dummy/B/leaf')
    

class TestRealModules(TestCase):
    
    
    def setUp(self):
        self.router = Router()
        self.app = TestApp(self.router)
        import examplepackage
        self.router.register_package(None, examplepackage, include_self=True)
        
    def test_default(self):
        res = self.app.get('/')
        self.assertEqual(res.body, 'package.__init__')
    
    def test_basic(self):
        res = self.app.get('/static')
        self.assertEqual(res.body, 'package.static')
    
    def test_leaf(self):
        res = self.app.get('/sub/leaf')
        self.assertEqual(res.body, 'package.__init__')
        

class TestRealRecursiveModules(TestRealModules):
    
    def setUp(self):
        self.router = Router()
        self.app = TestApp(self.router)
        from . import examplepackage
        self.router.register_package(None, examplepackage, recursive=True, include_self=True)
    
    def test_leaf(self):
        res = self.app.get('/sub/leaf')
        self.assertEqual(res.body, 'I am a leaf')


class TestTraversal(TestCase):
    
    def test_dont_fail_immediately(self):
        
        main = Router()
        a = main.register(None, Router())
        b = main.register(None, Router())
        a.register('/a', EchoApp('A says hello'))
        b.register('/b', EchoApp('B says hi'))
        b.register(None, EchoApp('catchall'))
        
        app = TestApp(main)
        res = app.get('/a')
        self.assertEqual(res.body, 'A says hello')
        res = app.get('/b')
        self.assertEqual(res.body, 'B says hi')
        res = app.get('/notthere')
        self.assertEqual(res.body, 'catchall')
        
        
        