
from . import *
from webstar.core import *
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
        p = Pattern('/gallery/{action}', constants=dict(controller='gallery'))
        data, path = p.match('/gallery/edit')
        self.assertEqual(data, dict(
            controller='gallery',
            action='edit',
        ))
        
    def test_constants_kwargs(self):
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
    
    def test_braces(self):
        p = Pattern(r'/{x:[a-z]{2,3}}')
        self.assertEqual(None, p.match('/a'))
        self.assertEqual(dict(x='bb'), p.match('/bb')[0])
        self.assertEqual(dict(x='ccc'), p.match('/ccc')[0])
        self.assertEqual(None, p.match('/dddd'))
    
    def test_format_key_error(self):
        p = Pattern(r'/{key}')
        self.assertEqual(p.format(key='value'), '/value')
        self.assertRaises(KeyError, p.format, notakey='value')
        self.assertRaises(FormatKeyError, p.format, notakey='value')
    
    def test_constant_errors(self):
        p = Pattern('/{key}', constants=dict(key='value'))
        self.assertEqual(p.format(), '/value')
        self.assertEqual(p.format(key='value'), '/value')
        self.assertRaises(FormatInvariantError, p.format, key='notvalue')
        
    def test_defaults(self):
        p = Pattern('/{key}', defaults=dict(key='value'))
        self.assertEqual(p.format(), '/value')
        self.assertEqual(p.format(key='value'), '/value')
        self.assertEqual(p.format(key='notvalue'), '/notvalue')
    
    def test_identifiable(self):
        p = Pattern('/hello')
        self.assertEqual(p.identifiable(), False)
        p = Pattern('/hello', name='hello')
        self.assertEqual(p.identifiable(), True)
        p = Pattern('/hello', constants=dict(name='hello'))
        self.assertEqual(p.identifiable(), True)
        p = Pattern('/hello', defaults=dict(name='hello'))
        self.assertEqual(p.identifiable(), False)
        p = Pattern('/{key}')
        self.assertEqual(p.identifiable(), True)

    def test_catchall(self):
        p = Pattern('')
        self.assertNotEqual(p.match(''), None)
        self.assertNotEqual(p.match('/'), None)
        self.assertNotEqual(p.match('/notempty'), None)
        
    def test_empty_path(self):
        p = Pattern('/')
        self.assertEqual(p.match(''), None)
        self.assertNotEqual(p.match('/'), None)
        self.assertEqual(p.match('/notempty'), None)
            
