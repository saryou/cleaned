import json
import re
from datetime import time, date, datetime
from enum import Enum
from typing import Any, Type, Union, List, Dict, Set, Optional, TypeVar, Sized, overload, Callable, cast

from .base import Field, Cleaned
from .errors import ValidationError, ErrorCode


T = TypeVar('T')
T1 = TypeVar('T1')
T2 = TypeVar('T2')
VT = TypeVar('VT')
Num = Union[int, float]
HashableT = TypeVar('HashableT')
CleanedT = TypeVar('CleanedT', bound=Cleaned)
EnumT = TypeVar('EnumT', bound=Enum)
StrT = TypeVar('StrT', bound=str)

C0 = TypeVar('C0', bound=Cleaned)
C1 = TypeVar('C1', bound=Cleaned)
C2 = TypeVar('C2', bound=Cleaned)
C3 = TypeVar('C3', bound=Cleaned)
C4 = TypeVar('C4', bound=Cleaned)
C5 = TypeVar('C5', bound=Cleaned)
C6 = TypeVar('C6', bound=Cleaned)
C7 = TypeVar('C7', bound=Cleaned)
C8 = TypeVar('C8', bound=Cleaned)
C9 = TypeVar('C9', bound=Cleaned)


class StrField(Field[str]):
    blank_pattern = re.compile(r'^\s*$')
    linebreak_pattern = re.compile(r'(\r\n|\r|\n)')
    linebreak_replacement = ' '
    default_multiline = False
    default_strip = True

    def __init__(self,
                 *,
                 blank: bool,
                 multiline: Optional[bool] = None,
                 strip: Optional[bool] = None,
                 pattern: Optional[str] = None,
                 length: Optional[int] = None,
                 min_length: Optional[int] = None,
                 max_length: Optional[int] = None,
                 one_of: Optional[Set[str]] = None):
        super().__init__()
        self.is_blankable = blank
        self.strip = strip
        self.pattern = re.compile(pattern) if pattern else None
        self.raw_pattern = pattern or ''
        self.multiline = multiline
        self.length = length
        self.min_length = min_length
        self.max_length = max_length
        self.one_of = one_of

    def value_to_str(self, value: Any) -> str:
        if isinstance(value, str):
            return value
        raise TypeError()

    def convert(self, value: Any) -> str:
        value = self.value_to_str(value)

        if (self.default_strip if self.strip is None else self.strip):
            value = value.strip()

        if not (self.default_multiline
                if self.multiline is None else self.multiline):
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

        if self.pattern and not self.pattern.match(value):
            self.raise_validation_error(
                value=value,
                default_message=f'The value must match: {self.raw_pattern}',
                code=ErrorCode.pattern)

        _validate(value, self, _LENGTH, _ONE_OF)


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
        _validate(value, self, _COMPARABLE, _ONE_OF)


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
        _validate(value, self, _COMPARABLE, _ONE_OF)


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
        _validate(value, self, _COMPARABLE, _ONE_OF)


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
        _validate(value, self, _COMPARABLE, _ONE_OF)


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
        _validate(value, self, _COMPARABLE, _ONE_OF)


class TagField(Field[str]):
    def __init__(self, *tags: str):
        super().__init__()
        self.tags = tags

    def convert(self, value: Any) -> str:
        for tag in self.tags:
            if tag == value:
                return tag
        raise TypeError()

    def validate(self, value: str):
        pass


class TaggedUnionField(Field[T]):
    @overload
    def __init__(self: 'TaggedUnionField[Union[C0, C1]]',
                 tag_field: str,
                 c0: Type[C0],
                 c1: Type[C1],
                 /):
        ...

    @overload
    def __init__(self: 'TaggedUnionField[Union[C0, C1, C2]]',
                 tag_field: str,
                 c0: Type[C0],
                 c1: Type[C1],
                 c2: Type[C2],
                 /):
        ...

    @overload
    def __init__(self: 'TaggedUnionField[Union[C0, C1, C2, C3]]',
                 tag_field: str,
                 c0: Type[C0],
                 c1: Type[C1],
                 c2: Type[C2],
                 c3: Type[C3],
                 /):
        ...

    @overload
    def __init__(self: 'TaggedUnionField[Union[C0, C1, C2, C3, C4]]',
                 tag_field: str,
                 c0: Type[C0],
                 c1: Type[C1],
                 c2: Type[C2],
                 c3: Type[C3],
                 c4: Type[C4],
                 /):
        ...

    @overload
    def __init__(self: 'TaggedUnionField[Union[C0, C1, C2, C3, C4, C5]]',
                 tag_field: str,
                 c0: Type[C0],
                 c1: Type[C1],
                 c2: Type[C2],
                 c3: Type[C3],
                 c4: Type[C4],
                 c5: Type[C5],
                 /):
        ...

    @overload
    def __init__(self: 'TaggedUnionField[Union[C0, C1, C2, C3, C4, C5, C6]]',
                 tag_field: str,
                 c0: Type[C0],
                 c1: Type[C1],
                 c2: Type[C2],
                 c3: Type[C3],
                 c4: Type[C4],
                 c5: Type[C5],
                 c6: Type[C6],
                 /):
        ...

    @overload
    def __init__(self: 'TaggedUnionField[Union[C0, C1, C2, C3, C4, C5, C6, C7]]',
                 tag_field: str,
                 c0: Type[C0],
                 c1: Type[C1],
                 c2: Type[C2],
                 c3: Type[C3],
                 c4: Type[C4],
                 c5: Type[C5],
                 c6: Type[C6],
                 c7: Type[C7],
                 /):
        ...

    @overload
    def __init__(self: 'TaggedUnionField[Union[C0, C1, C2, C3, C4, C5, C6, C7, C8]]',
                 tag_field: str,
                 c0: Type[C0],
                 c1: Type[C1],
                 c2: Type[C2],
                 c3: Type[C3],
                 c4: Type[C4],
                 c5: Type[C5],
                 c6: Type[C6],
                 c7: Type[C7],
                 c8: Type[C8],
                 /):
        ...

    @overload
    def __init__(self: 'TaggedUnionField[Union[C0, C1, C2, C3, C4, C5, C6, C7, C8, C9]]',
                 tag_field: str,
                 c0: Type[C0],
                 c1: Type[C1],
                 c2: Type[C2],
                 c3: Type[C3],
                 c4: Type[C4],
                 c5: Type[C5],
                 c6: Type[C6],
                 c7: Type[C7],
                 c8: Type[C8],
                 c9: Type[C9],
                 /):
        ...

    def __init__(self,
                 tag_field: str,
                 c0: Type[Cleaned],
                 c1: Type[Cleaned],
                 *cleaneds: Type[Cleaned]):
        super().__init__()
        self.tag_field = tag_field
        self.members = {c0, c1, *cleaneds}

        _mapping: Dict[str, Type[Cleaned]] = dict()
        for cl in self.members:
            field = cl._meta.fields.get(tag_field)
            if not isinstance(field, TagField):
                continue

            for tag in field.tags:
                assert tag not in _mapping,\
                    f'A tag `{tag}` is duplicated. '\
                    'All members of a tagged union must have unique tag.'
                _mapping[tag] = cl
        self.mapping = _mapping

    def convert(self, value: Any) -> T:
        if isinstance(value, str):
            value = json.loads(value)
        elif isinstance(value, Cleaned):
            value = value._data

        if isinstance(value, dict):
            tag = value.get(self.tag_field)
            if isinstance(tag, str) and (cl := self.mapping.get(tag)):
                return cast(T, cl(**value))
        raise TypeError()

    def validate(self, value: T):
        pass


class EitherField(Field[Union[T1, T2]]):
    def __init__(self,
                 t1: Field[T1],
                 t2: Field[T2]):
        super().__init__()
        self.t1 = t1
        self.t2 = t2

    def convert(self, value: Any) -> Union[T1, T2]:
        try:
            return self.t1.clean(value)
        except Exception:
            pass

        try:
            return self.t2.clean(value)
        except Exception:
            pass

        raise ValueError(f'Either {self.t1.__class__.__name__} '
                         f'and {self.t2.__class__.__name__} '
                         f'can not handle `{value}`.')

    def validate(self, value: Union[T1, T2]):
        pass


class ListField(Field[List[VT]]):
    def __init__(self,
                 value: Field[VT],
                 *,
                 length: Optional[int] = None,
                 min_length: Optional[int] = None,
                 max_length: Optional[int] = None):
        super().__init__()
        self.value = value
        self.length = length
        self.min_length = min_length
        self.max_length = max_length

    def convert(self, value: Any) -> List[VT]:
        if isinstance(value, str):
            value = json.loads(value)
        value = list(value)

        result: List[VT] = []
        errors: Dict[str, ValidationError] = {}
        for index, item in enumerate(value):
            try:
                result.append(self.value.clean(item))
            except ValidationError as e:
                errors[str(index)] = e
        if errors:
            raise ValidationError(errors)
        return result

    def validate(self, value: List[VT]):
        _validate(value, self, _LENGTH)


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
            raise ValidationError(list(error_items))
        return result

    def validate(self, value: Set[HashableT]):
        _validate(value, self, _LENGTH)


class DictField(Field[Dict[HashableT, VT]]):
    key: Field[HashableT]
    value: Field[VT]

    @overload
    def __init__(self: 'DictField[str, VT]',
                 value: Field[VT],
                 *,
                 length: Optional[int] = ...,
                 min_length: Optional[int] = ...,
                 max_length: Optional[int] = ...):
        pass

    @overload
    def __init__(self,
                 value: Field[VT],
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

    def convert(self, value: Any) -> Dict[HashableT, VT]:
        if isinstance(value, str):
            value = json.loads(value)
        value = dict(value)

        result: Dict[HashableT, VT] = {}
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

    def validate(self, value: Dict[HashableT, VT]):
        _validate(value, self, _LENGTH)


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


class EnumField(Field[EnumT]):
    def __init__(self,
                 enum: Union[Type[EnumT], Callable[[], Type[EnumT]]]):
        super().__init__()
        if isinstance(enum, type) and issubclass(enum, Enum):
            self._server = cast(Callable[[], Type[EnumT]], lambda: enum)
        else:
            self._server = cast(Callable[[], Type[EnumT]], enum)

    def convert(self, value: Any) -> EnumT:
        _type = self._server()

        if isinstance(value, _type):
            return value
        if isinstance(value, str):
            try:
                return _type[value]
            except KeyError:
                pass
        return _type(value)

    def validate(self, value: EnumT):
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
    if min_length is not None and len(value) < min_length:
        field.raise_validation_error(
            value=value,
            default_message='The length of the value '
            f'must be longer than or equal to {min_length}.',
            code=ErrorCode.min_length)
    if max_length is not None and len(value) > max_length:
        field.raise_validation_error(
            value=value,
            default_message='The length of the value '
            f'must be shorter than or equal to {max_length}.',
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


_COMPARABLE = 'comparable'
_LENGTH = 'length'
_ONE_OF = 'one_of'


def _validate(
        value: Any,
        field: Any,
        *methods: str):
    for m in methods:
        if m == _COMPARABLE:
            _validate_comparable(
                value=value,
                field=field,
                lt=field.lt,
                lte=field.lte,
                gt=field.gt,
                gte=field.gte)
        elif m == _LENGTH:
            _validate_length(
                value=value,
                field=field,
                length=field.length,
                min_length=field.min_length,
                max_length=field.max_length)
        elif m == _ONE_OF:
            _validate_one_of(
                value=value,
                field=field,
                one_of=field.one_of)
