from datetime import datetime as _datetime
import json as _json
from json.decoder import errmsg as _errmsg
from json.decoder import WHITESPACE as _WHITESPACE
from json.decoder import WHITESPACE_STR as _WHITESPACE_STR
from json.scanner import NUMBER_RE as _NUMBER_RE
import re as _re

_STRUCT_RE = _re.compile(r'([A-Z]\w*)\s*\(')

def _make_scanner(context):
    parse_object = context.parse_object
    parse_struct = context.parse_struct
    parse_array = context.parse_array
    parse_string = context.parse_string
    match_number = _NUMBER_RE.match
    parse_float = context.parse_float
    parse_int = context.parse_int
    parse_constant = context.parse_constant
    object_hook = context.object_hook
    object_pairs_hook = context.object_pairs_hook
    struct_hook = context.struct_hook

    params = []
    try:
        params.append(context.encoding)
    except AttributeError:
        pass
    params.append(context.strict)

    def _scan_once(string, idx):
        try:
            nextchar = string[idx]
        except IndexError:
            raise StopIteration

        if nextchar == '"':
            return parse_string(*([string, idx + 1] + params))
        elif nextchar == '{':
            return parse_object(*([(string, idx + 1)] + params +
                [_scan_once, object_hook, object_pairs_hook]))
        elif nextchar == '[':
            return parse_array((string, idx + 1), _scan_once)
        elif nextchar == 'n' and string[idx:idx + 4] == 'null':
            return None, idx + 4
        elif nextchar == 't' and string[idx:idx + 4] == 'true':
            return True, idx + 4
        elif nextchar == 'f' and string[idx:idx + 5] == 'false':
            return False, idx + 5

        m = match_number(string, idx)
        if m is not None:
            integer, frac, exp = m.groups()
            if frac or exp:
                res = parse_float(integer + (frac or '') + (exp or ''))
            else:
                res = parse_int(integer)
            return res, m.end()
        elif nextchar == 'N' and string[idx:idx + 3] == 'NaN':
            return parse_constant('NaN'), idx + 3
        elif nextchar == 'I' and string[idx:idx + 8] == 'Infinity':
            return parse_constant('Infinity'), idx + 8
        elif nextchar == '-' and string[idx:idx + 9] == '-Infinity':
            return parse_constant('-Infinity'), idx + 9

        m = _STRUCT_RE.match(string, idx)
        if m is not None:
            return parse_struct((string, m.end()), m.group(1),
                                _scan_once, struct_hook)
        else:
            raise StopIteration

    return _scan_once

def _JSONStruct(s_and_end, name, scan_once, struct_hook,
                _w = _WHITESPACE.match, _ws = _WHITESPACE_STR):
    s, end = s_and_end
    start = end
    values = []
    nextchar = s[end:end + 1]
    if nextchar in _ws:
        end = _w(s, end + 1).end()
        nextchar = s[end:end + 1]
    # Look-ahead for trivial empty struct
    if nextchar == ')':
        end += 1
    else:
        _append = values.append
        while True:
            try:
                value, end = scan_once(s, end)
            except StopIteration:
                raise ValueError(_errmsg("Expecting object", s, end))
            _append(value)
            nextchar = s[end:end + 1]
            if nextchar in _ws:
                end = _w(s, end + 1).end()
                nextchar = s[end:end + 1]
            end += 1
            if nextchar == ')':
                break
            elif nextchar != ',':
                raise ValueError(_errmsg("Expecting ',' delimiter", s, end))
            try:
                if s[end] in _ws:
                    end += 1
                    if s[end] in _ws:
                        end = _w(s, end + 1).end()
            except IndexError:
                pass
    try:
        return struct_hook(name, values), end
    except NotImplementedError:
        raise ValueError(_errmsg("Unsupported type %s" % name, s, start))
    except ValueError as ex:
        raise ex
    except Exception as ex:
        raise ValueError(_errmsg("Parse error: %s" % str(ex), s, start))

def struct_hook(name, values):
    try:
        if name == "Date":
            return _datetime.fromtimestamp(int(values[0])/1000.)
        elif name == "Set":
            return set(values[0])
        elif name == "Error":
            return Exception(*values)
    except (NotImplementedError, ValueError) as ex:
        raise Exception(str(ex))
    raise NotImplementedError

class JSONExtDecoder(_json.JSONDecoder):
    def __init__(self, struct_hook = struct_hook, *args, **kargs):
        _json.JSONDecoder.__init__(self, *args, **kargs)
        self.struct_hook = struct_hook
        self.parse_struct = _JSONStruct
        self.scan_once = _make_scanner(self)

class StructInt(int):
    def __str__(self):
        return "%s(%s)" % (self.name, ', '.join(self.values))

def struct_encode(o):
    if isinstance(o, _datetime):
        return ("Date", (int("%s%03d" % (o.strftime('%s'),
                                         o.microsecond/1000)), ))
    elif isinstance(o, (set, frozenset)):
        return ("Set", (list(o), ))
    elif isinstance(o, BaseException):
        return ("Error", o.args)
    raise NotImplementedError

class JSONExtEncoder(_json.JSONEncoder):
    def __init__(self, struct_encode = struct_encode, *args, **kargs):
        _json.JSONEncoder.__init__(self, *args, **kargs)
        self.struct_encode = struct_encode

    def default(self, o):
        try:
            name, values = self.struct_encode(o)
            si = StructInt()
            si.name = name
            si.values = [self.encode(v) for v in values]
            return si
        except NotImplementedError:
            return _json.JSONEncoder.default(self, o)

def dump(obj, fp, cls = JSONExtEncoder, *args, **kargs):
    return _json.dump(obj, fp, cls = cls, *args, **kargs)

def dumps(obj, cls = JSONExtEncoder, *args, **kargs):
    return _json.dumps(obj, cls = cls, *args, **kargs)

def load(fp, cls = JSONExtDecoder, *args, **kargs):
    return _json.load(fp, cls = cls, *args, **kargs)

def loads(s, cls = JSONExtDecoder, *args, **kargs):
    return _json.loads(s, cls = cls, *args, **kargs)
