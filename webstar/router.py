import re
import hashlib


class FormatError(ValueError):
    pass


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
        requirements = kwargs.pop('_requirements', {})
        if requirements:
            def make_requirement_predicate(name, regex):
                req_re = re.compile(regex + '$')
                def predicate(data):
                    return name in data and req_re.match(data[name])
                return predicate
            for name, regex in requirements.iteritems():
                self.predicates.append(make_requirement_predicate(name, regex))
        
        # Build predicates for nitrogen-style parsers.
        parsers = kwargs.pop('_parsers', {})
        if parsers:
            def make_parser_predicate(name, func):
                def predicate(data):
                    data[name] = func(data[name])
                    return True
                return predicate
            for name, func in parsers.iteritems():
                self.predicates.append(make_parser_predicate(name, func))
        
        self.predicates.extend(kwargs.pop('predicates', []))
        
        self._formatters = kwargs.pop('_formatters', {})

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

        for func in self.predicates:
            if not func(result):
                return

        return result, value[m.end():]

    def _format_data(self, data):
        for key, formatter in self._formatters.items():
            if key in data:
                if isinstance(formatter, basestring):
                    data[key] = formatter % data[key]
                else:
                    data[key] = formatter(data[key])

    def format(self, **kwargs):
        data = self.constants.copy()
        data.update(kwargs)
        self._format_data(data)

        out = self._format % data

        x = self.match(out)
        if x is None:
            raise FormatError('cannot match against output')
        m, d = x
        if d:
            raise FormatError('did not match all output')
        
        for k, v in m.iteritems():
            if k in data and data[k] != v:
                raise FormatError('got different value for %r: got %r, expected %r' % (k, v, data[k]))

        return out

