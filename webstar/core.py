"""Module containing tools to assist in building of WSGI routers.

This routing system works by tracking the UNrouted part of the request, and
watching how it changes as it passes through various routers.



"""

import collections
import logging
import posixpath


log = logging.getLogger(__name__)


HISTORY_ENVIRON_KEY = 'webstar.route'


def normalize_path(*segments):
    path = '/'.join(x for x in segments if x)
    if not path:
        return ''
    return '/' + posixpath.normpath(path).lstrip('/')


GenerateStep = collections.namedtuple('GenerateStep', 'segment head'.split())
RouteStep = collections.namedtuple('RouteStep', 'head consumed unrouted data router')


class Route(list):
    
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


class RouterInterface(object):
    
    def __repr__(self):
        return '<%s at 0x%x>' % (self.__class__.__name__, id(self))
    
    def route_step(self, path):
        """Yield a RouteStep for each possible route from this node."""
        raise NotImplementedError()
    
    def generate_step(self, data):
        """Yield a GenerateStep for each possible route from this node."""
        raise NotImplementedError()
        
    
    
    def route(self, path):
        """Route a given path, starting at this router."""    
        path = normalize_path(path)
        steps = self._route(self, path)
        if not steps:
            return
        return Route(path, steps)
    
    def _route(self, node, path):
        log.debug('_route: %r, %r' % (node, path))
        if not isinstance(node, RouterInterface):
            return []
        for step in node.route_step(path):
            res = self._route(step.head, step.unrouted)
            if res is not None:
                return [step] + res
    
    def __call__(self, environ, start):
        
        route = self.route(environ.get('PATH_INFO', ''))
        if route is None:
            return self.not_found_app(environ, start)
        
        # Build up wsgi.routing_args data
        args, kwargs = environ.setdefault('wsgiorg.routing_args', ((), {}))
        for step in route:
            kwargs.update(step.data)
        
        environ[HISTORY_ENVIRON_KEY] = route
        environ['PATH_INFO'] = route.unrouted
        environ['SCRIPT_NAME'] = environ.get('SCRIPT_NAME', '') + route.consumed
        
        return route.app(environ, start)
    
    def not_found_app(self, environ, start):
        start('404 Not Found', [('Content-Type', 'text/html')])
        return ['''
<html><head> 
<title>404 Not Found</title> 
</head><body> 
<h1>Not Found</h1> 
<p>The requested URL %s was not found on this server.</p> 
</body></html>
        '''.strip() % environ.get('PATH_INFO', 'UNKNOWN')]
        
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
        log.debug('_generate: %r, %r' % (node, data))
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



        







        

