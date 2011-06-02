from . import *
from webstar.core import *

class TestCode(TestCase):
    
    def test_normalize_path(self):
        self.assertEqual(normalize_path(), '')
        self.assertEqual(normalize_path(None), '')
        self.assertEqual(normalize_path('/'), '/')
        self.assertEqual(normalize_path('a/b'), '/a/b')
        self.assertEqual(normalize_path('a', 'b'), '/a/b')
        self.assertEqual(normalize_path('a', None, 'b'), '/a/b')
        self.assertEqual(normalize_path('a', '/b'), '/a/b')
        self.assertEqual(normalize_path('a//b/../c'), '/a/c')