import hashlib
import re

from . import core


class Pattern(core.PatternInterface):
    
    default_pattern = '[^/]+'
    default_format = 's'
    
    token_re = re.compile(r'''
        {                            
        ([a-zA-Z_][a-zA-Z0-9_-]*)      # group 1: name
        (?::                           # colon and group 2: pattern
          ([^:{]+(?:\{[^}]+\}[^:{]*)*) # zero or more chars, can use {#}
          (?::                         # colon and group 3: format string
            ([^}]+)
          )?
        )?
        }
    ''', re.X)

    def __init__(self, pattern, **kwargs):
        super(Pattern, self).__init__(**kwargs)
        self._raw = str(pattern or '')
        self._keys = set()
        self._compile()

    def __repr__(self):
        return '<%s:r%s>' % (self.__class__.__name__,
            repr(self._raw).replace('\\\\', '\\'))

    def _compile(self):
        self._segments = {}

        format = self.token_re.sub(self._compile_sub, self._raw)
        pattern = re.escape(format)
        
        for hash, (key, patt, form) in self._segments.items():
            pattern = pattern.replace(hash, '(?P<%s>%s)' % (key, patt), 1)
            format  = format.replace(hash, '%%(%s)%s' % (key, form), 1)

        self._format_string = format
        self._compiled = re.compile(pattern + r'(?=/|$)')

        del self._segments

    def _compile_sub(self, match):
        name = match.group(1)
        self._keys.add(name)
        patt = match.group(2) or self.default_pattern
        form = match.group(3) or self.default_format
        hash = 'x%s' % hashlib.md5(name).hexdigest()
        self._segments[hash] = (name, patt, form)
        return hash

    def _match(self, path):        
        m = self._compiled.match(path)
        if not m:
            return
        return m.groupdict(), path[m.end():]

    def identifiable(self):
        return bool(self.constants or self._keys)
        
    def _format(self, data):
        try:
            return self._format_string % data
        except KeyError as e:
            raise core.FormatKeyError(*e.args)


