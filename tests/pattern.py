
from . import *
from webstar.router import Pattern, FormatError

class TestPattern(TestCase):
    
    def test_match(self):
        p = Pattern(r'/{controller}/{action}/{id:\d+}')
        data, path = p.match('/gallery/photo/12')
        self.assertEqual(data, dict(
            controller='gallery',
            action='photo',
            id='12',
        ))
        self.assertEqual(path, '')
    
    def test_miss(self):
        p = Pattern('/something')
        m = p.match('/else')
        self.assertEqual(m, None)
    
    def test_incomplete_match(self):
        p = Pattern('/{word}')
        data, path = p.match('/one/two')
        self.assertEqual(data, dict(
            word='one'
        ))
        self.assertEqual(path, '/two')
        
    def test_format(self):
        p = Pattern('/{controller}/{action}')
        s = p.format(controller="news", action='archive')
        self.assertEqual(s, '/news/archive')
    
    def test_constants(self):
        p = Pattern('/gallery/{action}', controller='gallery')
        data, path = p.match('/gallery/edit')
        self.assertEqual(data, dict(
            controller='gallery',
            action='edit',
        ))
    
    def test_requirements(self):
        p = Pattern('/{id}', _requirements=dict(id=r'\d+'))
        m = p.match('/12')
        self.assertNotEqual(m, None)
        p = Pattern('/{mode}/{id}', _requirements=dict(mode='edit', id=r'\d+'))
        m = p.match('/edit/12')
        self.assertNotEqual(m, None)
    
    def test_requirement_miss(self):
        p = Pattern('/{id}', _requirements=dict(id=r'/d+'))
        m = p.match('/notanumber')
        self.assertEqual(m, None)
    
    def test_parsers(self):
        p = Pattern('/{id}', _parsers=dict(id=int))
        data, path = p.match('/12')
        self.assertEqual(data, dict(id=12))
    
    def test_formatters(self):
        p = Pattern('/{method:[A-Z]+}', _formatters=dict(method=str.upper))
        s = p.format(method='get')
        self.assertEqual(s, '/GET')
        
    def test_format_mismatch(self):
        p = Pattern('/{action:get}/{id:\d+}', _formatters=dict(id=int))
        self.assertRaises(FormatError, p.format, action='test', id=4)
    
    def test_predicate(self):
        p = Pattern('/{upper}', predicates=[lambda data: data['upper'].isupper()])
        m = p.match('/UPPER')
        self.assertNotEqual(m, None)
        m = p.match('/lower')
        self.assertEqual(m, None)
    
    
