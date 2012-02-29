from bisect import insort
import collections
import functools
import hashlib
import logging
import os
import posixpath
import re
import sys

from . import core
from . import pattern as patmod


log = logging.getLogger(__name__)


# Decorator for tagging routes in modules.
def route(pattern, func=None, **kwargs):
    if func is None:
        return functools.partial(route, pattern, **kwargs)
    route._counter += 1
    func.__dict__.setdefault('__route_args__', []).append((route._counter, pattern, func, kwargs))
    return func

route._counter = 0


class Router(core.RouterInterface):

    def __init__(self):
        super(Router, self).__init__()
        self._apps = []
        
    def children(self):
        return [(pattern.identifiable(), pattern._raw, node) for _, pattern, node in self._apps]
        
    def register(self, pattern, app=None, **kwargs):
        """Register directly, or use as a decorator.

        Params:
            pattern -- The pattern to match with. Should start with a '/'.
            app -- The app to register. If not provided this method returns
                a decorator which can be used to register with.

        """

        # We are being used directly here.
        if app:
            # We are creating a key here that will first respect the requested
            # priority of apps relative to each other, but in the case of
            # multiple apps at the same priority, respect the registration
            # order.
            
            priority = (-kwargs.pop('_priority', 0), len(self._apps))
            pattern = patmod.Pattern(pattern, **kwargs)
            insort(self._apps, (priority, pattern, app))
            
            # log.debug('register %r -> %r' % (pattern, app))
            
            return app

        # We are not being used directly, so return a decorator to do the
        # work later.
        return functools.partial(self.register, pattern, **kwargs)

    def register_package(self, pattern, package,
        recursive=False, testing=False, include_self=False, data_key=None,
        include_protected=False, **kwargs):
        
        if isinstance(package, basestring):
            package = __import__(package, fromlist=['hack'])
        
        data_key = data_key or '_'.join(reversed(package.__name__.split('.')))
        
        module_names = set()
        
        # Look for unloaded modules.
        for directory in package.__path__:
            if not os.path.exists(directory):
                continue
            for name in os.listdir(directory):
                init_path = os.path.join(directory, name, '__init__.py')
                if os.path.exists(init_path) or os.path.exists(init_path + 'c'):
                    module_names.add(name)
                    continue
                if not (name.endswith('.py') or name.endswith('.pyc')):
                    continue
                name = name.rsplit('.', 1)[0]
                if name == '__init__':
                    continue
                module_names.add(name)
        
        # Look for already imported modules; essentially for testing.
        if testing:
            for name, mod in sys.modules.iteritems():
                if mod is None or name != mod.__name__:
                    continue
                if name.startswith(package.__name__ + '.'):
                    module_names.add(name[len(package.__name__)+1:].split('.', 1)[0])
        
        for name in sorted(module_names):
            if name.startswith('_') and not include_protected:
                continue
            try:
                module_name = package.__name__ + '.' + name
                module = __import__(module_name, fromlist=['hack'])
            except ImportError as e:
                if e.args[0].endswith(' ' + module_name):
                    log.warn('could not import %r; skipping' % (package.__name__ + '.' + name))
                else:
                    raise
            else:
                subpattern = core.normalize_path(pattern, '{%s:%s}' % (data_key, name))
                if recursive and (
                    hasattr(module, '__path__') or
                    module.__file__.endswith('/__import__.py') or
                    module.__file__.endswith('/__import__.pyc')
                ):
                    self.register_package(subpattern, module,
                        recursive=recursive,
                        include_self=include_self,
                        testing=testing,
                        data_key=name + '_' + data_key,
                        include_protected=include_protected,
                        **kwargs
                    )
                else:
                    self.register_module(subpattern, module, **kwargs)
        
        if include_self:
            self.register_module(pattern, package, **kwargs)
    
    def register_module(self, pattern, module, **kwargs):
        if isinstance(module, str):
            module = __import__(module, fromlist=['hack'])
        
        # print repr(pattern), module.__name__

        router = module.__router__ = self.__class__()
        self.register(pattern, router, defaults=dict(__module__=module))
        
        args = []
        for func in module.__dict__.itervalues():
            if not hasattr(func, '__route_args__'):
                continue
            args.extend(func.__route_args__)
        args.sort()
        for arg_set in args:
            try:
                _, sub_pattern, func, sub_kwargs = arg_set
            except TypeError:
                continue
            router.register(sub_pattern, func, **sub_kwargs)
            
        default = getattr(module, '__app__', None)
        if default:
            router.register(None, default, **kwargs)
    
    def route_step(self, path):
        for _, pattern, node in self._apps:
            m = pattern.match(path)
            if m:
                data, unrouted = m
                yield core.RouteStep(
                    head=node,
                    router=self,
                    consumed=path[:-len(unrouted)] if unrouted else path,
                    unrouted=core.normalize_path(unrouted),
                    data=data
                )

    def generate_step(self, data):
        for _, pattern, node in self._apps:

            try:
                segment = pattern.format(**data)
            except core.FormatError:
                pass
            else:    
                yield core.GenerateStep(
                    segment=segment,
                    head=node,
                    identifiable=pattern.identifiable(),
                )




