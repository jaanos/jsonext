# jsonext
An extendable JSON parser for Python supporting the Date, Set and Error types

Works with Python 2.7 and Python 3.x.

## Examples

Simple decoding and encoding:
```python
>>> import jsonext
>>> json_str = '{"error": Error\t("Error!"), "date": Date( 1234567890000 ), "set": Set([ 1, "x", Error() ])}'
>>> json_obj = jsonext.loads(json_str)
>>> json_obj
{u'date': datetime.datetime(2009, 2, 14, 0, 31, 30), u'set': set([1, Exception(), u'x']), u'error': Exception(u'Error!',)}
>>> jsonext.dumps(json_obj)
'{"date": Date(1234567890000), "set": Set([1, Error(), "x"]), "error": Error("Error!")}'
```

Extending with a new type:
```python
import jsonext

class ObjectId:
    def __init__(self, id):
        self.id = id

    def __repr__(self):
        return "ObjectId(%s)" % repr(self.id)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, ObjectId):
            return self.id == other.id
        else:
            return self.id == other

def struct_hook(name, values):
    if name == "ObjectId":
        return ObjectId(values[0])
    return jsonext.struct_hook(name, values)

def struct_encode(o):
    if isinstance(o, ObjectId):
        return ("ObjectId", (o.id, ))
    return jsonext.struct_encode(o)
```

```python
>>> json_str = '[ObjectId("abcdef"), Set([ ObjectId( 123 ) ]), ObjectId(ObjectId(true))]'
>>> json_obj = jsonext.loads(json_str, struct_hook = struct_hook)
>>> json_obj
[ObjectId(u'abcdef'), frozenset({ObjectId(123)}), ObjectId(ObjectId(True))]
>>> jsonext.dumps(json_obj, struct_encode = struct_encode)
'[ObjectId("abcdef"), Set([ObjectId(123)]), ObjectId(ObjectId(true))]'
```
