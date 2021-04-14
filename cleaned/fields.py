import json
import re
from datetime import time, date, datetime
from typing import Any, Type, Union, List, Dict, Set, Optional, TypeVar, Sized, Literal, overload, Callable, cast

from .base import Field, Cleaned
from .errors import ValidationError, ErrorCode


T = TypeVar('T')
Num = Union[int, float]
HashableT = TypeVar('HashableT')
CleanedT = TypeVar('CleanedT', bound=Cleaned)


class StrField(Field[str]):
    blank_pattern = re.compile(r'^\s*$')
    linebreak_pattern = re.compile(r'(\r\n|\r|\n)')
    linebreak_replacement = ' '

    def __init__(self,
                 *,
                 blank: bool,
                 multiline: bool = False,
                 strip: bool = True,
                 length: Optional[int] = None,
                 min_length: Optional[int] = None,
                 max_length: Optional[int] = None,
                 one_of: Optional[Set[str]] = None):
        super().__init__()
        self.is_blankable = blank
        self.strip = strip
        self.multiline = multiline
        self.length = length
        self.min_length = min_length
        self.max_length = max_length
        self.one_of = one_of

    def convert(self, value: Any) -> str:
        if isinstance(value, str):
            pass
        elif isinstance(value, bytes):
            value = value.decode('utf-8')
        else:
            value = str(value)

        if self.strip:
            value = value.strip()
        if not self.multiline:
            value = self.linebreak_pattern.sub(
                self.linebreak_replacement, value)

        return value

    def validate(self, value: str):
        if self.blank_pattern.match(value):
            if self.is_blankable:
                # skip other validations for blank value
                return
            else:
                self.raise_validation_error(
                    value=value,
                    default_message='This field can not be blank.',
                    code=ErrorCode.blank)
        _validate(value, self, 'length', 'one_of')


class BoolField(Field[bool]):
    def __init__(self):
        super().__init__()

    def convert(self, value: Any) -> bool:
        return bool(value)

    def validate(self, value: bool):
        pass


class IntField(Field[int]):
    def __init__(self,
                 *,
                 lt: Optional[Num] = None,
                 lte: Optional[Num] = None,
                 gt: Optional[Num] = None,
                 gte: Optional[Num] = None,
                 one_of: Optional[Set[int]] = None):
        super().__init__()
        self.lt = lt
        self.lte = lte
        self.gt = gt
        self.gte = gte
        self.one_of = one_of

    def convert(self, value: Any) -> int:
        return int(value)

    def validate(self, value: int):
        _validate(value, self, 'comparable', 'one_of')


class FloatField(Field[float]):
    def __init__(self,
                 *,
                 lt: Optional[Num] = None,
                 lte: Optional[Num] = None,
                 gt: Optional[Num] = None,
                 gte: Optional[Num] = None,
                 one_of: Optional[Set[float]] = None):
        super().__init__()
        self.lt = lt
        self.lte = lte
        self.gt = gt
        self.gte = gte
        self.one_of = one_of

    def convert(self, value: Any) -> float:
        return float(value)

    def validate(self, value: float):
        _validate(value, self, 'comparable', 'one_of')


class TimeField(Field[time]):
    def __init__(self,
                 *,
                 lt: Optional[time] = None,
                 lte: Optional[time] = None,
                 gt: Optional[time] = None,
                 gte: Optional[time] = None,
                 one_of: Optional[Set[time]] = None):
        super().__init__()
        self.lt = lt
        self.lte = lte
        self.gt = gt
        self.gte = gte
        self.one_of = one_of

    def convert(self, value: Any) -> time:
        if isinstance(value, time):
            return value
        elif isinstance(value, datetime):
            return value.time()
        elif isinstance(value, date):
            return time.min
        return time.fromisoformat(value)

    def validate(self, value: time):
        _validate(value, self, 'comparable', 'one_of')


class DateField(Field[date]):
    def __init__(self,
                 *,
                 lt: Optional[date] = None,
                 lte: Optional[date] = None,
                 gt: Optional[date] = None,
                 gte: Optional[date] = None,
                 one_of: Optional[Set[date]] = None):
        super().__init__()
        self.lt = lt
        self.lte = lte
        self.gt = gt
        self.gte = gte
        self.one_of = one_of

    def convert(self, value: Any) -> date:
        if isinstance(value, date):
            return value
        elif isinstance(value, datetime):
            return value.date()
        elif isinstance(value, (int, float)):
            return datetime.fromtimestamp(value).date()
        return datetime.fromisoformat(value).date()

    def validate(self, value: date):
        _validate(value, self, 'comparable', 'one_of')


class DatetimeField(Field[datetime]):
    def __init__(self,
                 *,
                 lt: Optional[datetime] = None,
                 lte: Optional[datetime] = None,
                 gt: Optional[datetime] = None,
                 gte: Optional[datetime] = None,
                 one_of: Optional[Set[datetime]] = None):
        super().__init__()
        self.lt = lt
        self.lte = lte
        self.gt = gt
        self.gte = gte
        self.one_of = one_of

    def convert(self, value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        elif isinstance(value, date):
            return datetime.combine(value, time.min)
        elif isinstance(value, (int, float)):
            return datetime.fromtimestamp(value)
        return datetime.fromisoformat(value)

    def validate(self, value: datetime):
        _validate(value, self, 'comparable', 'one_of')


class ListField(Field[List[T]]):
    def __init__(self,
                 value: Field[T],
                 *,
                 length: Optional[int] = None,
                 min_length: Optional[int] = None,
                 max_length: Optional[int] = None):
        super().__init__()
        self.value = value
        self.length = length
        self.min_length = min_length
        self.max_length = max_length

    def convert(self, value: Any) -> List[T]:
        if isinstance(value, str):
            value = json.loads(value)
        value = list(value)

        result: List[T] = []
        errors: Dict[str, ValidationError] = {}
        for index, item in enumerate(value):
            try:
                result.append(self.value.clean(item))
            except ValidationError as e:
                errors[str(index)] = e
        if errors:
            raise ValidationError(errors)
        return result

    def validate(self, value: List[T]):
        _validate(value, self, 'length')


class SetField(Field[Set[HashableT]]):
    def __init__(self,
                 value: Field[HashableT],
                 *,
                 length: Optional[int] = None,
                 min_length: Optional[int] = None,
                 max_length: Optional[int] = None):
        super().__init__()
        self.value = value
        self.length = length
        self.min_length = min_length
        self.max_length = max_length

    def convert(self, value: Any) -> Set[HashableT]:
        if isinstance(value, str):
            value = json.loads(value)
        value = iter(value)

        result: Set[HashableT] = set()
        error_items: List[ValidationError.Item] = []
        for item in value:
            try:
                result.add(self.value.clean(item))
            except ValidationError as e:
                error_items.extend(e.items)
        if error_items:
            raise ValidationError(error_items)
        return result

    def validate(self, value: Set[HashableT]):
        _validate(value, self, 'length')


class DictField(Field[Dict[HashableT, T]]):
    key: Field[HashableT]
    value: Field[T]

    @overload
    def __init__(self: 'DictField[str, T]',
                 value: Field[T],
                 *,
                 length: Optional[int] = ...,
                 min_length: Optional[int] = ...,
                 max_length: Optional[int] = ...):
        pass

    @overload
    def __init__(self,
                 value: Field[T],
                 key: Field[HashableT],
                 *,
                 length: Optional[int] = ...,
                 min_length: Optional[int] = ...,
                 max_length: Optional[int] = ...):
        pass

    def __init__(self,
                 value,
                 key=None,
                 *,
                 length: Optional[int] = None,
                 min_length: Optional[int] = None,
                 max_length: Optional[int] = None):
        super().__init__()
        self.value = value
        self.key = key or StrField(blank=False, multiline=False)
        self.length = length
        self.min_length = min_length
        self.max_length = max_length

    def convert(self, value: Any) -> Dict[HashableT, T]:
        if isinstance(value, str):
            value = json.loads(value)
        value = dict(value)

        result: Dict[HashableT, T] = {}
        errors: Dict[str, ValidationError] = {}
        for k, v in value.items():
            try:
                _key = self.key.clean(k)
                try:
                    _value = self.value.clean(v)
                    result[_key] = _value
                except ValidationError as e:
                    errors[f'{_key}'] = e
            except ValidationError as e:
                errors[f'{k}:key'] = e
                try:
                    self.value.clean(k)
                except ValidationError as e:
                    errors[f'{k}'] = e
        if errors:
            raise ValidationError(errors)
        return result

    def validate(self, value: Dict[HashableT, T]):
        _validate(value, self, 'length')


class NestedField(Field[CleanedT]):
    def __init__(self,
                 cleaned: Union[Type[CleanedT], Callable[[], Type[CleanedT]]]):
        super().__init__()
        if isinstance(cleaned, type) and issubclass(cleaned, Cleaned):
            self._server = cast(Callable[[], Type[CleanedT]], lambda: cleaned)
        else:
            self._server = cast(Callable[[], Type[CleanedT]], cleaned)

    def convert(self, value: Any) -> CleanedT:
        if isinstance(value, str):
            value = json.loads(value)

        _type = self._server()

        if isinstance(value, Cleaned):
            return _type(**value._data)

        return _type(**dict(value))

    def validate(self, value: CleanedT):
        pass


def _validate_comparable(
        value: Any,
        field: Field[Any],
        lt: Optional[Any],
        lte: Optional[Any],
        gt: Optional[Any],
        gte: Optional[Any]):
    if lt is not None and value >= lt:
        field.raise_validation_error(
            value=value,
            default_message=f'The value must be less than {lt}.',
            code=ErrorCode.lt)
    if lte is not None and value > lte:
        field.raise_validation_error(
            value=value,
            default_message=f'The value must be less than or equal to {lte}.',
            code=ErrorCode.lte)
    if gt is not None and value <= gt:
        field.raise_validation_error(
            value=value,
            default_message=f'The value must be greater than {gt}.',
            code=ErrorCode.gt)
    if gte is not None and value < gte:
        field.raise_validation_error(
            value=value,
            default_message='The value '
            f'must be greater than or equal to {gte}.',
            code=ErrorCode.gte)


def _validate_length(
        value: Sized,
        field: Field[Sized],
        length: Optional[int],
        min_length: Optional[int],
        max_length: Optional[int]):
    if length is not None and len(value) != length:
        field.raise_validation_error(
            value=value,
            default_message='The length of the value '
            f'must be equal to {length}.',
            code=ErrorCode.length)
    if min_length is not None and len(value) > min_length:
        field.raise_validation_error(
            value=value,
            default_message='The length of the value '
            f'must be less than or equal to {min_length}.',
            code=ErrorCode.min_length)
    if max_length is not None and len(value) < max_length:
        field.raise_validation_error(
            value=value,
            default_message='The length of the value '
            f'must be greater than or equal to {max_length}.',
            code=ErrorCode.max_length)


def _validate_one_of(
        value: HashableT,
        field: Field[HashableT],
        one_of: Optional[Set[HashableT]]):
    if one_of is not None and value not in one_of:
        field.raise_validation_error(
            value=value,
            default_message='The value must be one of {one_of}',
            code=ErrorCode.one_of)


def _validate(
        value: Any,
        field: Any,
        *methods: Union[Literal['comparable'],
                        Literal['length'],
                        Literal['one_of']]):
    for m in methods:
        if m == 'comparable':
            _validate_comparable(
                value=value,
                field=field,
                lt=field.lt,
                lte=field.lte,
                gt=field.gt,
                gte=field.gte)
        elif m == 'length':
            _validate_length(
                value=value,
                field=field,
                length=field.length,
                min_length=field.min_length,
                max_length=field.max_length)
        elif m == 'one_of':
            _validate_one_of(
                value=value,
                field=field,
                one_of=field.one_of)
