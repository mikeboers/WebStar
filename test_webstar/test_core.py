from . import *
from webstar.core import *
from webstar.router import Router

class TestCore(TestCase):
    
    def test_normalize_path(self):
        self.assertEqual(normalize_path(), '/')
        self.assertEqual(normalize_path(None), '/')
        self.assertEqual(normalize_path('/'), '/')
        self.assertEqual(normalize_path('a/b'), '/a/b')
        self.assertEqual(normalize_path('a', 'b'), '/a/b')
        self.assertEqual(normalize_path('a', None, 'b'), '/a/b')
        self.assertEqual(normalize_path('a', '/b'), '/a/b')
        self.assertEqual(normalize_path('a//b/../c'), '/a/c')
        self.assertEqual(normalize_path('/./a/./b/../c'), '/a/c')
        self.assertEqual(normalize_path('/trailing/'), '/trailing')
        self.assertEqual(normalize_path('//'), '/')
        
    
    def test_normalize(self):
        router = Router()
        app = TestApp(router)
        res = app.get('/trailing_slash/')
        self.assertEquals(res.status, '301 Moved Permanently')
        self.assertEquals(res.headers['Location'], '/trailing_slash')