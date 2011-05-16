from bisect import insort
import collections
import hashlib
import logging
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
        def ReRouter_register(app):
            self.register(pattern, app, **kwargs)
            return app
        return ReRouter_register

    def route_step(self, path):
        for _, pattern, app in self._apps:
            m = pattern.match(path)
            if m:
                kwargs, path = m
                return core.RoutingStep(next=app, path=path, data=kwargs)

    def generate_step(self, data):
        log.debug('generate_step(%r, %r)' % (self, data))
        for _, pattern, app in self._apps:
            # Skip patterns that are not identifiable.
            if not (pattern._keys or pattern.constants):
                continue
            # Filter out unmatching constant data.
            if any(k in data and data[k] != v for k, v in
                pattern.constants.iteritems()):
                continue
            try:
                return core.GenerationStep(segment=pattern.format(**data), next=app)
            except KeyError:
                pass
                # log.exception('KeyError while generating')






