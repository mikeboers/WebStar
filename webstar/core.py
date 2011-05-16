"""Module containing tools to assist in building of WSGI routers.

This routing system works by tracking the UNrouted part of the request, and
watching how it changes as it passes through various routers.



"""

import collections
import logging
import posixpath


log = logging.getLogger(__name__)


HISTORY_ENVIRON_KEY = 'webstar.route.history'


def normalize_path(*segments):
    path = '/'.join(x for x in segments if x)
    if not path:
        return ''
    return '/' + posixpath.normpath(path).lstrip('/')


GenerateStep = collections.namedtuple('GenerateStep', 'segment next'.split())
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
    
    def url_for(self, _strict=True, **data):
        for i, chunk in enumerate(self):
            if chunk.router is not None:
                return chunk.router.generate(data, history=self[i:], strict=_strict)
    
    @property
    def consumed(self):
        return ''.join(x.consumed or '' for x in self)
    
    @property
    def app(self):
        return self[-1].head
    
    @property
    def history(self):
        return self
    
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
    def __init__(self, path, router, data):
        self.path = path
        self.router = router
        self.data = data
        msg = 'stopped generating at %r by %r with %r' % (path, router, data)
        ValueError.__init__(self, msg)


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
    
    def generate(self, new_data, history=None, strict=False):
        path = []
        route_i = -1
        route_data = new_data.copy()
        apply_route_data = history is not None
        nodes = []
        node = self
        log.debug('Starting route generation with %r from %r:' % (new_data, history))
        while isinstance(node, RouterInterface):
            nodes.append(node)
            route_i += 1
            if apply_route_data and (len(history) <= route_i or
                history[route_i].router is not node):
                apply_route_data = False
            if apply_route_data:
                route_data.update(history[route_i].data)
                route_data.update(new_data)
            step = node.generate_step(route_data)
            if not step:
                if strict:
                    raise GenerationError(path, node, route_data)
                return None
            log.debug('\t%d: apply_data=%r, %r from %r' % (route_i + 1, apply_route_data, step, node))

            node = step.next
            path.append(step.segment)
        
        log.debug('\tDONE.')
        return normalize_path('/'.join(path))
    
    def url_for(self, _strict=True, **data):
        return self.generate(data, strict=_strict)



        







        

