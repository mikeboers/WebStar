import re
import hashlib


class FormatError(Exception):
    pass

class FormatKeyError(FormatError, KeyError): pass
class FormatMatchError(FormatError, ValueError): pass
class FormatIncompleteMatchError(FormatError, ValueError): pass
class FormatPredicateError(FormatError, ValueError): pass
class FormatDataEqualityError(FormatError, ValueError): pass

class Pattern(object):

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
        
        self.constants = kwargs
        self.constants.update(kwargs.pop('constants', {}))
        
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

    def match(self, value):
        """Match this pattern against some text. Returns the matched data, and
        the unmatched string, or None if there is no match.
        """

        m = self._compiled.match(value)
        if not m:
            return

        result = self.constants.copy()
        result.update(m.groupdict())

        if not self._test_predicates(result):
            return

        return result, value[m.end():]

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


