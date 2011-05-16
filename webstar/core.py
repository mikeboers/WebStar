"""Module containing tools to assist in building of WSGI routers.

This routing system works by tracking the UNrouted part of the request, and
watching how it changes as it passes through various routers.



"""

import collections
import logging
import posixpath


log = logging.getLogger(__name__)


HISTORY_ENVIRON_KEY = 'webstar.route.history'


class History(list):
    
    @classmethod
    def from_environ(cls, environ):
        """Gets the list of routing history from the environ."""
        obj = environ.get(HISTORY_ENVIRON_KEY)
        if not obj:
            return cls(environ.get('PATH_INFO', ''))
        return obj
    
    def __init__(self, path):
        self.update(path)
    
    def update(self, unrouted, consumed=None, router=None, data=None):
        """Sets the current unrouted path and adds to routing history."""
        
        if not unrouted:
            unrouted = ''
        else:
            unrouted = '/' + posixpath.normpath(unrouted.lstrip('/'))
        
        self.append(HistoryChunk(
            unrouted=unrouted,
            consumed=consumed,
            router=router,
            data=data
        ))
    
    def url_for(self, _strict=True, **data):
        for i, chunk in enumerate(self):
            if chunk.router is not None:
                return chunk.router.generate(data, history=self[i:], strict=_strict)
    
    @property
    def consumed(self):
        return ''.join(x.consumed or '' for x in self)
    
    def __repr__(self):
        return '<%s:%s>' % (self.__class__.__name__, list.__repr__(self))
        

Route = collections.namedtuple('Route', 'history app unrouted'.split())
GenerateStep = collections.namedtuple('GenerateStep', 'segment next'.split())
RouteStep = collections.namedtuple('RouteStep', 'next consumed unrouted data')

_HistoryChunk = collections.namedtuple('HistoryChunk', 'unrouted consumed router data'.split())
class HistoryChunk(_HistoryChunk):
    def __new__(cls, unrouted, consumed=None, router=None, data=None):
        return _HistoryChunk.__new__(cls, unrouted, consumed, router, data or {})


def get_route_data(environ):
    history = History.from_environ(environ)
    if not history:
        return {}
    data = {}
    for chunk in history:
        data.update(chunk.data)
    return data


class RoutingError(ValueError):
    def __init__(self, history, router, path):
        self.history = history
        self.router = router
        self.path = path
        msg = 'failed on route %r at %r with %r' % (history, router, path)
        ValueError.__init__(self, msg)

class GenerationError(ValueError):
    def __init__(self, path, router, data):
        self.path = path
        self.router = router
        self.data = data
        msg = 'stopped generating at %r by %r with %r' % (path, router, data)
        ValueError.__init__(self, msg)


class Router(object):
    
    def __repr__(self):
        return '<%s at 0x%x>' % (self.__class__.__name__, id(self))
    
    def route_step(self, path):
        """Return RouteStep, or None if the path can't be routed."""
        raise NotImplementedError()
    
    def generate_step(self, data):
        """Return GenerateStep, or None if a segment can't be generated."""
        raise NotImplementedError()
    
    def modify_path(self, path):
        """Modify the path downstream of the router during generation.
        
        Allows a router to mutate the unrouted path. The route_step should
        undo this mutation.
        
        """
        return path
    
    def route(self, path, strict=False):
        """Route a given path, starting at this router.
        
        If strict, a router that can't route a step will result in a raised
        RoutingError exception.
        
        """
        log.debug('Starting route %r:' % path)
        steps = 0
        history = History(path)
        router = self
        while hasattr(router, 'route_step'):
            steps += 1
            # print 'a', router, path
            step = router.route_step(path)
            if step is None:
                if strict:
                    raise RoutingError(history, router, path)
                return None
            log.debug('\t%d: %r' % (steps, step))
            history.update(
                unrouted=step.unrouted, 
                consumed=step.consumed,
                router=router,
                data=step.data
            )
            router = step.next
            path = step.unrouted
        log.debug('\tDONE.')
        return Route(
            history=history,
            app=router,
            unrouted=path
        )
    
    def __call__(self, environ, start):
        
        history = History.from_environ(environ)
        path = environ.get('PATH_INFO', '')
            
        route = self.route(path)
        if route is None:
            return self.not_found_app(environ, start)
        
        # Build up wsgi.routing_args data
        args, kwargs = environ.setdefault('wsgiorg.routing_args', ((), {}))
        for step in route.history:
            kwargs.update(step.data)
        
        environ[HISTORY_ENVIRON_KEY] = route.history
        environ['PATH_INFO'] = route.unrouted
        environ['SCRIPT_NAME'] = environ.get('SCRIPT_NAME', '') + route.history.consumed
        
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
        while node is not None and hasattr(node, 'generate_step'):
            nodes.append(node)
            route_i += 1
            if apply_route_data and (len(history) <= route_i or
                history[route_i].router is not node):
                apply_route_data = False
            if apply_route_data:
                route_data.update(history[route_i].data)
                route_data.update(new_data)
            step = node.generate_step(route_data)
            if step is None:
                if strict:
                    raise GenerationError(path, node, route_data)
                return None
            log.debug('\t%d: apply_data=%r, %r from %r' % (route_i + 1, apply_route_data, step, node))
            if not isinstance(step, GenerateStep):
                step = GenerateStep(*step)

            node = step.next
            path.append(step.segment)
        
        log.debug('\tDONE.')
        out = ''
        for i, segment in reversed(list(enumerate(path))):
            node = nodes[i]
            out = segment + out
            if hasattr(node, 'modify_path'):
                out = node.modify_path(out)
        
        return str(out)
    
    def url_for(self, _strict=True, **data):
        return self.generate(data, strict=_strict)



        







        

