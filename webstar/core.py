"""Module containing tools to assist in building of WSGI routers.

This routing system works by tracking the UNrouted part of the request, and
watching how it changes as it passes through various routers.



"""

import abc
import collections
import logging
import posixpath
import re

log = logging.getLogger(__name__)


HISTORY_ENVIRON_KEY = 'webstar.route'


    
    
def normalize_path(*segments):
    path = '/'.join(x for x in segments if x)
    if not path:
        return '/'
    return '/' + posixpath.normpath(path).strip('/')


GenerateStep = collections.namedtuple('GenerateStep', 'segment head'.split())
RouteStep = collections.namedtuple('RouteStep', 'head consumed unrouted data router')


class Route(list):
    
    @staticmethod
    def from_environ(environ):
        return environ.get(HISTORY_ENVIRON_KEY)
    
    def __init__(self, path, steps):
        self.append(RouteStep(
            unrouted=path,
            head=None,
            consumed=None,
            data={},
            router=None,
        ))
        self.extend(steps)
    
    def url_for(self, _strict=True, **kwargs):
        for i, chunk in enumerate(self):
            if chunk.router is not None:
                data = self.data.copy()
                data.update(kwargs)
                url = chunk.router.generate(data)
                if _strict and not url:
                    raise GenerationError('could not generate URL for %r, relative to %r' % (data, self[0].unrouted))
                return url
        if _strict:
            raise GenerationError('no routers')
    
    @property
    def consumed(self):
        return ''.join(x.consumed or '' for x in self)
    
    @property
    def app(self):
        return self[-1].head
   
    @property
    def unrouted(self):
        return self[-1].unrouted
    
    @property
    def data(self):
        data = {}
        for step in self:
            data.update(step.data)
        return data
    
    def __repr__(self):
        return '<%s:%s>' % (self.__class__.__name__, list.__repr__(self))
        

def get_route_data(environ):
    route = environ.get(HISTORY_ENVIRON_KEY, None)
    return route.data if route else {}


class GenerationError(ValueError):
    pass


class FormatError(Exception):
    pass
class FormatKeyError(FormatError, KeyError): pass
class FormatInvariantError(FormatError, ValueError): pass
class FormatMatchError(FormatError, ValueError): pass
class FormatIncompleteMatchError(FormatError, ValueError): pass
class FormatPredicateError(FormatError, ValueError): pass
class FormatDataEqualityError(FormatError, ValueError): pass


class PatternInterface(object):
    __metaclass__ = abc.ABCMeta
    
    @abc.abstractmethod
    def _match(self, path):
        '''Return (data, unmatched_path) if matches, else None.'''
        return None
    
    @abc.abstractmethod
    def identifiable(self):
        '''Return True if this pattern is able to be specified by a data dict.
        
        Eg. if the pattern does not capture anything, nor does it enforce any
        constants/invariants upon the data then it is not identifiable and
        should not be used for URL generation.
        
        '''
        return False 
        
    @abc.abstractmethod
    def _format(self, data):
        '''Return a string, None, or raise a FormatError'''
        pass
        
    def __init__(self, *args, **kwargs):
        
        self.constants = kwargs
        self.constants.update(kwargs.pop('constants', {}))
        
        self.defaults = kwargs.pop('defaults', {})
        
        self.predicates = []
        
        # Build predicates for nitrogen-style requirements.
        nitrogen_requirements = kwargs.pop('_requirements', {})
        if nitrogen_requirements:
            def make_requirement_predicate(name, regex):
                req_re = re.compile(regex + '$')
                def predicate(data):
                    return name in data and req_re.match(data[name])
                return predicate
            for name, regex in nitrogen_requirements.iteritems():
                self.predicates.append(make_requirement_predicate(name, regex))
        
        # Build predicates for nitrogen-style parsers.
        nitrogen_parsers = kwargs.pop('_parsers', {})
        if nitrogen_parsers:
            def make_parser_predicate(name, func):
                def predicate(data):
                    data[name] = func(data[name])
                    return True
                return predicate
            for name, func in nitrogen_parsers.iteritems():
                self.predicates.append(make_parser_predicate(name, func))
        
        self.predicates.extend(kwargs.pop('predicates', []))
        
        self.formatters = []
        
        nitrogen_formatters = kwargs.pop('_formatters', {})
        if nitrogen_formatters:
            def make_bc_formatter(name, func):
                if isinstance(func, str):
                    format = func
                    func = lambda value: format % value
                def formatter(data):
                    data[name] = func(data[name])
                return formatter
            for name, format in nitrogen_formatters.iteritems():
                self.formatters.append(make_bc_formatter(name, format))
        
        self.formatters.extend(kwargs.pop('formatters', []))
        
        super(PatternInterface, self).__init__(*args)
        
    def _test_predicates(self, data):
        for func in self.predicates:
            if not func(data):
                return
        return True
           
    def match(self, path):
        """Match this pattern against some text. Returns the matched data, and
        the unmatched string, or None if there is no match.
        """
        
        m = self._match(path)
        if not m:
            return
        
        data, unmatched = m
        
        result = self.constants.copy()
        result.update(data)

        if not self._test_predicates(result):
            return
        
        return result, unmatched
    

    
    def format(self, **kwargs):
        """Return a path which encodes some of the data in kwargs.
        
        The returned path will re-match to data that does not conflict with
        the original arguments. A path does not need to encode ALL of the data
        requested, but any data that it would recover by re-matching it would
        not conflict.
        
        """
        
        if any(k in kwargs and kwargs[k] != v for k, v in
            self.constants.iteritems()):
            raise FormatInvariantError('supplied data does not match constants')
            
        data = self.defaults.copy()
        data.update(kwargs)
        data.update(self.constants)

        for func in self.formatters:
            func(data)
        
        out = self._format(data)

        x = self.match(out)
        if x is None:
            raise FormatMatchError('final result does not satisfy original pattern')
        m, d = x
        if d:
            raise FormatIncompleteMatchError('final result was not fully captured by original pattern')

        # Untested.
        if not self._test_predicates(data):
            raise FormatPredicateError('supplied data does not satisfy predicates')

        # Untested.
        for k, v in m.iteritems():
            if k in self.constants and self.constants[k] != v:
                raise FormatInvariantError('re-match resolved bad value for %r: got %r, require %r' % (k, v, data[k]))
            if k in data and data[k] != v:
                raise FormatDataEqualityError('re-match resolved different value for %r: got %r, expected %r' % (k, v, data[k]))
        
        return out
               
    
    
class RouterInterface(object):
    __metaclass__ = abc.ABCMeta
    
    def __repr__(self):
        return '<%s at 0x%x>' % (self.__class__.__name__, id(self))
    
    @abc.abstractmethod
    def route_step(self, path):
        """Yield a RouteStep for each possible route from this node."""
        while False:
            yield None
    
    @abc.abstractmethod
    def generate_step(self, data):
        """Yield a GenerateStep for each possible route from this node."""
        while False:
            yield None
        
    def route(self, path):
        """Route a given path, starting at this router."""    
        path = normalize_path(path)
        # log.debug('starting route for %r' % path)
        steps = self._route(self, path, 0)
        # log.debug('done')
        if not steps:
            return
        return Route(path, steps)
    
    def _route(self, node, path, depth):
        if not isinstance(node, RouterInterface):
            log.debug('%d: found leaf -> %r' % (depth, node))
            return []
        log.debug('%d: trying %r with %r' % (depth, path, node))
        for step in node.route_step(path):
            res = self._route(step.head, step.unrouted, depth + 1)
            if res is not None:
                log.debug('%d: got %r' % (depth, res))
                return [step] + res
            else:
                pass
                log.debug('%d: deadend' % (depth, ))
    
    def __call__(self, environ, start):
        
        path_info = environ.get('PATH_INFO', '')
        normalized = normalize_path(path_info)
        if path_info and path_info != normalized:
            res = self.not_normalized_app(environ, start, normalized)
            if res:
                return res
            
        route = self.route(path_info)
        if route is None:
            res = self.not_found_app(environ, start)
            if res:
                return res
        
        # Build up wsgi.routing_args data
        args, kwargs = environ.setdefault('wsgiorg.routing_args', ((), {}))
        for step in route:
            kwargs.update(step.data)
        
        environ[HISTORY_ENVIRON_KEY] = route
        environ['PATH_INFO'] = route.unrouted
        environ['SCRIPT_NAME'] = environ.get('SCRIPT_NAME', '') + route.consumed
        
        return route.app(environ, start)
    
    def not_normalized_app(self, environ, start, normalized):
        path_info = environ.get('PATH_INFO')
        log.info('redirecting via 301 to normalize %r' % path_info)
        start('301 Moved Permanently', [
            ('Location', normalized),
            ('Content-Type', 'text/plain'),
        ])
        return ['''
<html><head> 
<title>301 Moved Permanently</title> 
</head><body> 
<h1>Malformed URL</h1> 
<p>Your requested URL (%s) is being redirected to the canonical location (%s).</p> 
</body></html>
        '''.strip() % (path_info, normalized)]
        
    def not_found_app(self, environ, start):
        path_info = environ.get('PATH_INFO')
        log.info('404 for %r' % path_info)
        start('404 Not Found', [('Content-Type', 'text/html')])
        return ['''
<html><head> 
<title>404 Not Found</title> 
</head><body> 
<h1>Not Found</h1> 
<p>The requested URL (%s) was not found on this server.</p> 
</body></html>
        '''.strip() % path_info]
        
    def generate(self, *args, **kwargs):
        data = dict()
        for arg in args:
            data.update(arg)
        data.update(kwargs)
        steps = self._generate(self, data)
        if not steps:
            return
        return normalize_path('/'.join(step.segment for step in steps))

    def _generate(self, node, data):
        data = data.copy()
        # log.debug('_generate: %r, %r' % (node, data))
        if not isinstance(node, RouterInterface):
            return []
        for step in node.generate_step(data):
            res = self._generate(step.head, data)
            if res is not None:
                return [step] + res
                
    def url_for(self, _strict=True, **data):
        url = self.generate(data)
        if _strict and not url:
            raise GenerationError('could not generate URL for %r' % data)
        return url

