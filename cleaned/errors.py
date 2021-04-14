from typing import NamedTuple, overload, Optional, Dict, List, Iterable


class ErrorCode:
    required = 'required'
    conversion = 'conversion'
    blank = 'blank'
    lt = 'lt'
    lte = 'lte'
    gt = 'gt'
    gte = 'gte'
    length = 'length'
    min_length = 'min_length'
    max_length = 'max_length'
    one_of = 'one_of'


class ValidationError(Exception):
    class Item(NamedTuple):
        message: str
        code: str

    items: List[Item]
    nested: Dict[str, 'ValidationError']

    @overload
    def __init__(self,
                 message: str,
                 code: str):
        ...

    @overload
    def __init__(self, message: 'ValidationError'):
        ...

    @overload
    def __init__(self, message: Dict[str, 'ValidationError']):
        ...

    @overload
    def __init__(self,
                 message: List[Item],
                 code: Optional[Dict[str, 'ValidationError']] = None):
        ...

    def __init__(self, message, code=None):
        if isinstance(message, str):
            self.items = [self.Item(message, code)]
            self.nested = dict()
        elif isinstance(message, ValidationError):
            self.items = message.items
            self.nested = message.nested
        elif isinstance(message, dict):
            self.items = []
            self.nested = message
        elif isinstance(message, list):
            self.items = message
            self.nested = code or dict()

    def _flatten_items(self) -> Iterable[Item]:
        yield from self.items
        for v in self.nested.values():
            yield from v._flatten_items()

    def to_flat_codes(self) -> List[str]:
        return [i.code for i in self._flatten_items()]
