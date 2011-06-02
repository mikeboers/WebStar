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


class Router(core.RouterInterface):

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
            insort(self._apps, (priority, patmod.Pattern(pattern, **kwargs), app))
            return app

        # We are not being used directly, so return a decorator to do the
        # work later.
        return functools.partial(self.register, pattern, **kwargs)

    def register_package(self, pattern, package, recursive=False, testing=False):
        if isinstance(package, basestring):
            package = __import__(package, fromlist=['hack'])
            
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
            for name in sys.modules:
                if name.startswith(package.__name__ + '.'):
                    module_names.add(name[len(package.__name__)+1:].split('.', 1)[0])
        
        for name in sorted(module_names):
            try:
                module_name = package.__name__ + '.' + name
                module = __import__(module_name, fromlist=['hack'])
            except ImportError as e:
                if e.args[0].endswith(' ' + module_name):
                    log.warn('could not import %r; skipping' % (package.__name__ + '.' + name))
                else:
                    raise
            else:
                subpattern = core.normalize_path(pattern, name)
                if recursive and (
                    hasattr(module, '__path__') or
                    module.__file__.endswith('/__import__.py') or
                    module.__file__.endswith('/__import__.pyc')
                ):
                    self.register_package(subpattern, module, recursive=recursive, testing=testing)
                else:
                    self.register_module(subpattern, module)
        
        self.register_module(pattern, package)
    
    def register_module(self, pattern, module):
        log.debug('register_module %r -> %r' % (pattern, module))
        self.register(pattern, ModuleRouter(module))
    
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
        # log.debug('generate_step(%r, %r)' % (self, data))
        for _, pattern, node in self._apps:
            
            # Skip patterns that are not identifiable.
            if not (pattern._keys or pattern.constants):
                continue
            
            try:
                segment = pattern.format(**data)
            except core.FormatError:
                pass
            else:    
                yield core.GenerateStep(segment=segment, head=node)


class ModuleRouter(Router):

    def __init__(self, module, reload=False):
        self.module = module
        self.reload = reload
        self._last_mtime = self.getmtime()
        self._scanned = False
        self._assert_scanned()
        
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

