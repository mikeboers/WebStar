
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
        self._constants = kwargs
        self._keys = set()

        self._requirements = kwargs.pop('_requirements', {})
        self._requirements = dict((k, re.compile(v + '$'))
            for k, v in self._requirements.items())

        self._parsers = kwargs.pop('_parsers', {})
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
            return None

        result = self._constants.copy()
        result.update(m.groupdict())

        for key, pattern in self._requirements.items():
            if not key in result or not pattern.match(result[key]):
                return None

        self._parse_data(result)

        return result, value[m.end():]

    def _parse_data(self, data):
        for key, callback in self._parsers.items():
            if key in data:
                data[key] = callback(data[key])

    def _format_data(self, data):
        for key, formatter in self._formatters.items():
            if key in data:
                if isinstance(formatter, basestring):
                    data[key] = formatter % data[key]
                else:
                    data[key] = formatter(data[key])

    def format(self, **kwargs):
        data = self._constants.copy()
        data.update(kwargs)
        self._format_data(data)

        out = self._format % data

        x = self.match(out)
        if x is None:
            raise FormatError('cannot match against output')
        m, d = x
        if d:
            raise FormatError('did not match all output')

        self._parse_data(data)

        for k, v in m.iteritems():
            if k in data and data[k] != v:
                raise FormatError('got different value for %r: got %r, expected %r' % (k, v, data[k]))

        return out


