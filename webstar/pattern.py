import hashlib
import re

from . import core

class FormatKeyError(core.FormatError, KeyError): pass
class FormatMatchError(core.FormatError, ValueError): pass
class FormatIncompleteMatchError(core.FormatError, ValueError): pass
class FormatPredicateError(core.FormatError, ValueError): pass
class FormatDataEqualityError(core.FormatError, ValueError): pass

class Pattern(core.PatternInterface):

    def identifiable(self): pass
    
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

    def __init__(self, raw, **kwargs):

        self._raw = raw
        self._keys = set()
        super(Pattern, self).__init__(**kwargs)
        
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

        self._format = format
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

    def _match(self, value):
        """Match this pattern against some text. Returns the matched data, and
        the unmatched string, or None if there is no match.
        """

        m = self._compiled.match(value)
        if not m:
            return

        return m.groupdict(), value[m.end():]

    def _test_predicates(self, data):
        for func in self.predicates:
            if not func(data):
                return
        return True
    
    def format(self, **kwargs):
        data = self.constants.copy()
        data.update(kwargs)
        
        for func in self.formatters:
            func(data)

        try:
            out = self._format % data
        except KeyError as e:
            raise FormatKeyError(*e.args)
        
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
            if k in data and data[k] != v:
                raise FormatDataEqualityError('re-match resolved different value for %r: got %r, expected %r' % (k, v, data[k]))

        return out


