from dataclasses import dataclass
from typing import overload, Optional, Dict, List, Sequence, Mapping, Iterable, Tuple, Union, cast


class ErrorCode:
    required = 'required'
    conversion = 'conversion'
    blank = 'blank'
    pattern = 'pattern'
    lt = 'lt'
    lte = 'lte'
    gt = 'gt'
    gte = 'gte'
    length = 'length'
    min_length = 'min_length'
    max_length = 'max_length'
    one_of = 'one_of'


ValidationErrorItemType = Union[
    str,
    Tuple[str, Optional[str]],
    'ValidationError.Item',
]

ValidationErrorItemTypes = Union[
    ValidationErrorItemType,
    Sequence[ValidationErrorItemType],
]

ValidationErrorNestedType = Mapping[
    str,
    Union[
        ValidationErrorItemTypes,
        'ValidationError',
    ],
]


class ValidationError(Exception):
    @dataclass
    class Item:
        message: str
        code: Optional[str] = None

    items: List[Item]
    nested: Dict[str, 'ValidationError']

    @overload
    def __init__(self, message: str, code: str):
        ...

    @overload
    def __init__(self, message: 'ValidationError'):
        ...

    @overload
    def __init__(self, message: ValidationErrorNestedType):
        ...

    @overload
    def __init__(self,
                 message: ValidationErrorItemTypes,
                 code: Optional[ValidationErrorNestedType] = None):
        ...

    def __init__(self, message, code=None):
        if isinstance(code, str):
            # message: str
            # code: str
            self.items = [self.Item(message, code)]
            self.nested = dict()
        elif isinstance(message, ValidationError):
            # message: ValidationError
            self.items = message.items
            self.nested = message.nested
        elif isinstance(message, Mapping):
            # message: ValidationErrorNestedType
            self.items = []
            self.nested = _to_nested(message)
        else:
            # message: ValidationErrorItemTypes
            # code: Optional[ValidationErrorNestedType]
            self.items = _to_items(message)
            self.nested = _to_nested(code or dict())

    def _flatten_items(self) -> Iterable[Item]:
        yield from self.items
        for v in self.nested.values():
            yield from v._flatten_items()

    def to_flat_codes(self) -> List[str]:
        return [i.code for i in self._flatten_items() if i.code is not None]


def _to_nested(data: ValidationErrorNestedType) -> Dict[str, ValidationError]:
    return {k: ValidationError(v) for k, v in data.items()}


def _to_items(items: ValidationErrorItemTypes) -> List[ValidationError.Item]:
    if isinstance(items, Sequence):
        return [_to_item(cast(ValidationErrorItemType, i)) for i in items]
    else:
        return [_to_item(items)]


def _to_item(item: ValidationErrorItemType) -> ValidationError.Item:
    if isinstance(item, str):
        return ValidationError.Item(item)
    elif isinstance(item, tuple):
        return ValidationError.Item(item[0], item[1])
    else:
        return item
