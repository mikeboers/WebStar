  
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
            
'''







def test_routing_path_setup():

    router = ReRouter()

    @router.register(r'/{word:one|two|three}')
    def one(environ, start):
        start('200 OK', [('Content-Type', 'text-plain')])
        yield core.get_route_data(environ)['word']

    @router.register(r'/x-{num:\d+}', _parsers=dict(num=int))
    def two(environ, start):
        start('200 OK', [('Content-Type', 'text-plain')])
        yield '%02d' % core.get_route_data(environ)['num']

    @router.register(r'/{key:pre\}post}')
    def three(environ, start, *args, **kwargs):
        start('200 OK', [('Content-Type', 'text-plain')])
        yield core.get_route_data(environ)['key']

    app = webtest.TestApp(router)

    res = app.get('/one/two')
    assert res.body == 'one'
    # pprint(core.get_history(res.environ))
    _assert_next_history_step(res,
            path='/two',
            router=router
    )

    res = app.get('/x-4/x-3/x-2/one')
    # print res.body
    assert res.body == '04'
    # pprint(core.get_history(res.environ))
    _assert_next_history_step(res,
        path='/x-3/x-2/one', router=router, _data={'num': 4})
    
    try:
        app.get('/-does/not/exist')
        assert False
    except HTTPNotFound:
        pass

    try:
        app.get('/one_extra/does-not-exist')
        assert False
    except HTTPNotFound:
        pass

    res = app.get('/pre}post')
    assert res.body == 'pre}post'


def test_route_building():

    router = ReRouter()

    @router.register(r'/{word:one|two|three}')
    def one(environ, start):
        start('200 OK', [('Content-Type', 'text-plain')])
        yield core.get_route_history(environ)[-1]['word']

    @router.register(r'/x-{num:\d+}', _parsers=dict(num=int))
    def two(environ, start):
        kwargs = core.get_route_history(environ)[-1]
        start('200 OK', [('Content-Type', 'text-plain')])
        yield '%02d' % kwargs.data['num']

    @router.register('')
    def three(environ, start):
        start('200 OK', [('Content-Type', 'text/plain')])
        yield 'empty'

    app = webtest.TestApp(router)

    res = app.get('/x-1')
    route = core.get_route_history(res.environ)
    print repr(res.body)
    print repr(route.url_for(num=2))

    res = app.get('/x-1/one/blah')
    route = core.get_route_history(res.environ)
    pprint(route)
    print repr(res.body)
    print repr(route.url_for(word='two'))



if __name__ == '__main__':
    import nose; nose.run(defaultTest=__name__)
    '''
