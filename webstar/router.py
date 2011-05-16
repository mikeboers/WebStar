from bisect import insort
import collections
import functools
import hashlib
import logging
import os
import posixpath
import re

from . import core
from .pattern import Pattern, FormatError


log = logging.getLogger(__name__)


class Router(core.Router):

    def __init__(self):
        self._apps = []

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
            insort(self._apps, (priority, Pattern(pattern, **kwargs), app))
            return app

        # We are not being used directly, so return a decorator to do the
        # work later.
        return functools.partial(self.register, pattern, **kwargs)

    def register_package(self, pattern, package, recursive=False):
        if isinstance(package, basestring):
            package = __import__(package)
        module_names = set()
        for directory in package.__path__:
            for name in os.listdir(directory):
                if not (name.endswith('.py') or name.endswith('.pyc')):
                    continue
                name = name.rsplit('.', 1)[0]
                if name == '__init__':
                    continue
                module_names.add(name)
        for name in sorted(module_names):
            try:
                module = __import__(package.__name__ + '.' + name)
            except ImportError:
                log.warn('could not import %r' % (package.__name__ + '.' + name))
            else:
                self.register_module(
                    core.normalize_path(pattern, name),
                    module
                )
        self.register_module(pattern, package)
    
    def register_module(self, pattern, module):
        self.register(pattern, ModuleRouter(module))
    
    def route_step(self, path):
        for _, pattern, app in self._apps:
            m = pattern.match(path)
            if m:
                data, unrouted = m
                return core.RouteStep(
                    next=app,
                    consumed=path[:-len(unrouted)] if unrouted else path,
                    unrouted=unrouted,
                    data=data
                )

    def generate_step(self, data):
        # log.debug('generate_step(%r, %r)' % (self, data))
        for _, pattern, app in self._apps:
            # Skip patterns that are not identifiable.
            if not (pattern._keys or pattern.constants):
                continue
            # Filter out unmatching constant data.
            if any(k in data and data[k] != v for k, v in
                pattern.constants.iteritems()):
                continue
            try:
                return core.GenerateStep(segment=pattern.format(**data), next=app)
            except KeyError:
                pass
                # log.exception('KeyError while generating')



class ModuleRouter(Router):

    def __init__(self, module, reload=False):
        self.module = module
        self.reload = reload
        self._last_mtime = self.getmtime()
        self._scanned = False
        
    def getmtime(self):
        return os.path.getmtime(self.module.__file__)

    def _assert_scanned(self):
        if self.reload:
            mtime = self.getmtime()
            if self._last_mtime != mtime:
                self._last_mtime = mtime
                self._app = None
                log.debug('reloading module %r' % self.module.__name__)
                reload(self.module)
                self._scanned = False
        if not self._scanned:
            self._apps = []
            main = getattr(self.module, '__app__', None)
            if main:
                self.register('', main)
        
    def route_step(self, path):
        self._assert_scanned()
        return super(ModuleRouter, self).route_step(path)

    def generate_step(self, data): 
        self._assert_scanned()
        return super(ModuleRouter, self).generate_step(data)

    def __repr__(self):
        return '<%s.%s of %s>' % (self.__class__.__module__, self.__class__.__name__, self.module.__name__)

    

