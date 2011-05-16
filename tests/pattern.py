
from . import *
from webstar.pattern import *

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
    
    def test_nitrogen_requirements(self):
        p = Pattern('/{id}', _requirements=dict(id=r'\d+'))
        m = p.match('/12')
        self.assertNotEqual(m, None)
        p = Pattern('/{mode}/{id}', _requirements=dict(mode='edit', id=r'\d+'))
        m = p.match('/edit/12')
        self.assertNotEqual(m, None)
    
    def test_nitrogen_requirement_miss(self):
        p = Pattern('/{id}', _requirements=dict(id=r'/d+'))
        m = p.match('/notanumber')
        self.assertEqual(m, None)
    
    def test_nitrogen_parsers(self):
        p = Pattern('/{id}', _parsers=dict(id=int))
        data, path = p.match('/12')
        self.assertEqual(data, dict(id=12))
    
    def test_nitrogen_formatters(self):
        p = Pattern('/{method:[A-Z]+}', _formatters=dict(method=str.upper))
        s = p.format(method='get')
        self.assertEqual(s, '/GET')
    
    def test_nitrogen_format_string(self):
        p = Pattern('/{number:\d+}', _formatters=dict(number='%04d'))
        s = p.format(number=12)
        self.assertEqual(s, '/0012')
        
    def test_format_mismatch(self):
        p = Pattern('/{id:\d+}')
        self.assertRaises(FormatMatchError, p.format, id='notanumber')
    
    def test_format_incomplete_rematch(self):
        p = Pattern('/{segment}')
        self.assertRaises(FormatIncompleteMatchError, p.format, segment='one/two')
    
    def test_predicate(self):
        p = Pattern('/{upper}', predicates=[lambda data: data['upper'].isupper()])
        m = p.match('/UPPER')
        self.assertNotEqual(m, None)
        m = p.match('/lower')
        self.assertEqual(m, None)
    
    def test_format_string(self):
        p = Pattern(r'/{year:\d+:04d}', _parsers=dict(year=int))
        data, path = p.match('/2012')
        self.assertEqual(data, dict(year=2012))
        s = p.format(year=12)
        self.assertEqual(s, '/0012')
    
