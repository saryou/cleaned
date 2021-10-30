# cleaned

pypi: https://pypi.org/project/clnd/

## Overview

`cleaned` is a declarative data validator.

## Examples

```python
import json
import cleaned as cl


class Request(cl.Cleaned):
    username = cl.Str(pattern='^[a-zA-Z_]+$', blank=False, min_length=3)
    password = cl.Str(blank=False, min_length=8)
    age = cl.Int()


def register_user_api(request_json: str) -> ...:
    dirty_data = json.loads(request_json)
    cleaned_data = Request(**dirty_data)

    # username matches ^[a-zA-Z_]+$ and it has at least 3 characters
    username = cleaned_data.username

    # password is at least 8 characters
    password = cleaned_data.password

    # age is a int value
    age = cleaned_data.age

    # do something with the data
    print(username, password, age)
    ...


register_user_api(json.dumps({
    'username': 'user',
    'password': 'KJF83h9q3FAS',
    'age': '20',
}))


try:
    Request(username='invalid format', password='short')
except cl.ValidationError as e:
    print(e.nested['username'])
    # ('The value must match: ^[a-zA-Z_]+$', 'pattern')
    print(e.nested['password'])
    # ('The length of the value must be longer than or equal to 8.', 'min_length')
    print(e.nested['age'])
    # ('This field is required', 'required')
```

## Static Typing

mypy can handle almost all cleaned values in the library.

```python
import cleaned as cl
import enum


class Examples(cl.Cleaned):
    class NestedExample(cl.Cleaned):
        a = cl.Int()

    class EnumExample(enum.Enum):
        a = 1
        b = 2

    a = cl.Either(cl.Int(), cl.Str(blank=False))
    b = cl.Int().opt()
    c = cl.Dict(key=cl.Int(), value=cl.Float().opt()).opt()
    d = cl.Nested(NestedExample)
    e = cl.Enum(EnumExample)
    f = cl.List(cl.Nested(NestedExample))
    g = cl.List(cl.Nested(lambda: Examples))


ex = Examples()

reveal_type(ex.a)
# Revealed type is 'Union[builtins.int*, builtins.str*]'

reveal_type(ex.b)
# Revealed type is 'Union[builtins.int*, None]'

reveal_type(ex.c)
# Revealed type is 'Union[builtins.dict*[builtins.int*, Union[builtins.float*, None]], None]'

reveal_type(ex.d)
# Revealed type is 'Examples.NestedExample*'

reveal_type(ex.e)
# Revealed type is 'Examples.EnumExample*'

reveal_type(ex.f)
# Revealed type is 'builtins.list*[Examples.NestedExample*]'

reveal_type(ex.g)
# Revealed type is 'builtins.list*[hoge.Examples*]'
```
