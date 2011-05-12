import re
import hashlib


class FormatError(ValueError):
    pass

class FormatMatchError(FormatError): pass
class FormatIncompleteMatchError(FormatError): pass
class FormatPredicateError(FormatError): pass
class FormatDataEqualityError(FormatError): pass

class Pattern(object):

    default_pattern = '[^/]+'
    token_re = re.compile(r'''
        {                           # start of keyword match
        ([a-zA-Z_]\w*)              # group 1: name
        (?::(                       # colon and group 2: pattern
        [^}\\]*(?:\\.[^}\\]*)*      # zero or more chars. } can be escaped.
        ))?                         # the colon and pattern are optional
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

        self._hash_to_key = {}
        self._hash_to_pattern = {}

        format = self.token_re.sub(self._compile_sub, self._raw)

        pattern = re.escape(format)
        for hash, patt in self._hash_to_pattern.items():
            pattern = pattern.replace(hash, patt, 1)

        for hash, key in self._hash_to_key.items():
            format = format.replace(hash, '%%(%s)s' % key, 1)

        self._format = format
        self._compiled = re.compile(pattern + r'(?=/|$)')

        del self._hash_to_key
        del self._hash_to_pattern

    def _compile_sub(self, match):
        name = match.group(1)
        self._keys.add(name)
        patt = match.group(2) or self.default_pattern
        hash = 'x%s' % hashlib.md5(name).hexdigest()
        self._hash_to_key[hash] = name
        self._hash_to_pattern[hash] = '(?P<%s>%s)' % (name, patt)
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

        out = self._format % data

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


