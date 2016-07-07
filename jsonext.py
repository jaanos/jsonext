from datetime import datetime
from json import JSONDecoder, JSONEncoder
from json.decoder import errmsg, WHITESPACE, WHITESPACE_STR
from json.scanner import NUMBER_RE
import re

STRUCT_RE = re.compile(r'([A-Z]\w*)\(')

def make_scanner(context):
    parse_object = context.parse_object
    parse_struct = context.parse_struct
    parse_array = context.parse_array
    parse_string = context.parse_string
    match_number = NUMBER_RE.match
    encoding = context.encoding
    strict = context.strict
    parse_float = context.parse_float
    parse_int = context.parse_int
    parse_constant = context.parse_constant
    object_hook = context.object_hook
    object_pairs_hook = context.object_pairs_hook
    struct_hook = context.struct_hook

    def _scan_once(string, idx):
        try:
            nextchar = string[idx]
        except IndexError:
            raise StopIteration

        if nextchar == '"':
            return parse_string(string, idx + 1, encoding, strict)
        elif nextchar == '{':
            return parse_object((string, idx + 1), encoding, strict,
                _scan_once, object_hook, object_pairs_hook)
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

        m = STRUCT_RE.match(string, idx)
        if m is not None:
            return parse_struct((string, m.end()), m.group(1), encoding,
                                strict, _scan_once, struct_hook)
        else:
            raise StopIteration

    return _scan_once

def JSONStruct(s_and_end, name, encoding, strict, scan_once, struct_hook,
               _w = WHITESPACE.match, _ws = WHITESPACE_STR):
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
                raise ValueError(errmsg("Expecting object", s, end))
            _append(value)
            nextchar = s[end:end + 1]
            if nextchar in _ws:
                end = _w(s, end + 1).end()
                nextchar = s[end:end + 1]
            end += 1
            if nextchar == ')':
                break
            elif nextchar != ',':
                raise ValueError(errmsg("Expecting ',' delimiter", s, end))
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
        raise ValueError(errmsg("Unsupported type %s" % name, s, start))
    except ValueError as ex:
        raise ex
    except Exception as ex:
        raise ValueError(errmsg("Parse error: %s" % str(ex), s, start))

def date_hook(name, values):
    try:
        if name == "Date":
            return datetime.fromtimestamp(int(values[0])/1000)
    except (NotImplementedError, ValueError) as ex:
        raise Exception(str(ex))
    raise NotImplementedError

class JSONExtDecoder(JSONDecoder):
    def __init__(self, struct_hook = date_hook, *args, **kargs):
        JSONDecoder.__init__(self, *args, **kargs)
        self.struct_hook = struct_hook
        self.parse_struct = JSONStruct
        self.scan_once = make_scanner(self)
