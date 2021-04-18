from typing import TypeVar, Generic, overload, Any, Type, Dict, Tuple, Union, Optional, Callable

from .errors import ValidationError, ErrorCode
from .utils import Undefined


T = TypeVar('T')
FieldT = TypeVar('FieldT', bound='Field')
CleanedT = TypeVar('CleanedT', bound='Cleaned')
_UNDEFINED = Undefined()


class Field(Generic[T]):
    _propname: str
    _label = ''
    _desc = ''
    _default: Union[Undefined, T, Callable[[], T]] = _UNDEFINED

    expected_exceptions_for_convert: Tuple[Type[Exception], ...] =\
        (ValueError, TypeError)

    def clean(self, value: Any = _UNDEFINED) -> T:
        if value is _UNDEFINED:
            if isinstance(self._default, Undefined):
                self.raise_required_error(
                    value=value,
                    default_message='This field is required',
                    code=ErrorCode.required)
            elif callable(self._default):
                return self._default()
            else:
                return self._default

        try:
            value = self.convert(value)
        except self.expected_exceptions_for_convert as e:
            self.raise_conversion_error(
                value=value,
                default_message=f'Failed to convert `{value}`'
                f' for {self.__class__.__name__}',
                code=ErrorCode.conversion,
                exception=e)

        self.validate(value)
        return value

    def convert(self, value: Any) -> T:
        raise NotImplementedError()

    def validate(self, value: T):
        raise NotImplementedError()

    def default(self: FieldT, value: Union[T, Callable[[], T]]) -> FieldT:
        self._default = value
        return self

    @property
    def label(self) -> str:
        return self._label

    @property
    def desc(self) -> str:
        return self._desc

    def describe(self: FieldT,
                 label: Optional[str] = None,
                 desc: Optional[str] = None) -> FieldT:
        if label is not None:
            self._label = label
        if desc is not None:
            self._desc = desc
        return self

    @overload
    def __get__(self: FieldT,
                instance: Union[None, 'Field'],
                owner=None) -> FieldT:
        ...

    @overload
    def __get__(self, instance: 'Cleaned', owner=None) -> T:
        ...

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        return instance._data[self._propname]

    def __set__(self, instance, val):
        if instance is None:
            return
        instance._data[self._propname] = self.clean(val)

    def __set_name__(self, owner, name):
        self._propname = name

    def raise_required_error(self,
                             value: Any,
                             default_message: str,
                             code: str):
        raise ValidationError(default_message, code)

    def raise_conversion_error(self,
                               value: Any,
                               default_message: str,
                               code: str,
                               exception: Exception):
        raise ValidationError(default_message, code)

    def raise_validation_error(self,
                               value: T,
                               default_message: str,
                               code: str):
        raise ValidationError(default_message, code)

    def opt(self: 'Field[T]', omissible: bool = True) -> 'OptionalField[T]':
        return OptionalField(self, omissible=omissible)


class OptionalField(Field[Optional[T]]):
    field: Field[T]

    def __init__(self,
                 field: Field[T],
                 omissible: bool = True):
        self.field = field
        self.omissible = omissible

    def clean(self, value: Any = _UNDEFINED) -> Optional[T]:
        if value is _UNDEFINED and self.omissible:
            return None
        return super().clean(value)

    def convert(self, value: Any) -> Optional[T]:
        if value is None:
            return None
        return self.field.convert(value)

    def validate(self, value: Optional[T]):
        if value is not None:
            self.field.validate(value)


class CleanedMeta:
    def __init__(self, fields: Dict[str, Field]) -> None:
        self._fields = fields

    def __copy__(self):
        return CleanedMeta(self.fields)

    @property
    def fields(self) -> Dict[str, Field]:
        return self._fields.copy()


class CleanedBuilder(type):
    def __new__(mcs, name: str, bases: Tuple, fields: Dict[str, Any]):
        cleaned_fields: Dict[str, Field] = dict()
        for base in bases:
            base_meta = getattr(base, '_meta', None)
            if base_meta:
                for k, v in base_meta._fields.items():
                    cleaned_fields[k] = v

        for key, value in fields.items():
            if isinstance(value, Field):
                assert key not in cleaned_fields, \
                    'Overriding fields of cleaned should be avoided. ' \
                    'Cleaned: {} field: {}'.format(name, key)
                cleaned_fields[key] = value

        fields['_meta'] = CleanedMeta(cleaned_fields)
        cls = type.__new__(mcs, name, bases, fields)

        return cls


class Cleaned(metaclass=CleanedBuilder):
    _meta: CleanedMeta
    _data: Dict[str, Any]

    def __init__(self, **kwargs) -> None:
        self._data = dict()

        errors: Dict[str, ValidationError] = dict()

        for key, field in self._meta._fields.items():
            try:
                self._data[key] = field.clean(kwargs.get(key, _UNDEFINED))
            except ValidationError as e:
                errors[key] = e

        if errors:
            raise ValidationError(errors)

    def __repr__(self) -> str:
        data = ', '.join('{}: {}'.format(
            k, getattr(self, k)) for k in self._meta._fields)
        return '<{}.{} ({}) at {}>'.format(
            self.__module__, self.__class__.__qualname__, data, id(self))

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._data)
