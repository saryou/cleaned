from typing import TypeVar, Generic, overload, Any, Type, Dict, Tuple, Union,\
    Optional, Callable, List, Set, Iterable

from .errors import ValidationError, ErrorCode
from .utils import Undefined


T = TypeVar('T')
VT = TypeVar('VT')
FieldT = TypeVar('FieldT', bound='Field')
DependableT = TypeVar('DependableT', bound='Dependable')
CleanedT = TypeVar('CleanedT', bound='Cleaned')
_UNDEFINED = Undefined()


class Dependable(Generic[T]):
    _propname: str

    @overload
    def __get__(self: DependableT,
                instance: Union[None, 'Dependable'],
                owner=None) -> DependableT:
        ...

    @overload
    def __get__(self, instance: 'Cleaned', owner=None) -> T:
        ...

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        try:
            return instance._data[self._propname]
        except KeyError as e:
            raise DirtyFieldAccess(self._propname) from e

    def __set__(self, instance, val):
        raise AttributeError(f'cannot assign to field `{self._propname}`')

    def __set_name__(self, owner, name):
        self._propname = name


class DirtyFieldAccess(Exception):
    def __init__(self, key: str):
        self.key = key


class ConstraintAccess(Exception):
    def __init__(self, key: str):
        self.key = key


class Field(Dependable[T]):
    _label = ''
    _desc = ''
    _default: Union[Undefined, T, Callable[[], T]] = _UNDEFINED

    expected_exceptions_for_convert: Tuple[Type[Exception], ...] =\
        (ValueError, TypeError)

    def clean(self, value: Any) -> T:
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
    def has_default(self) -> bool:
        return self._default is not _UNDEFINED

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
        raise ValidationError(default_message, code) from exception

    def raise_validation_error(self,
                               value: T,
                               default_message: str,
                               code: str):
        raise ValidationError(default_message, code)

    def opt(self: 'Field[T]') -> 'OptionalField[T]':
        opt = OptionalField(self)
        opt.describe(
            label=self.label,
            desc=self.desc)
        if not isinstance(self._default, Undefined):
            opt.default(self._default)
        return opt

    def cleaned_property(self, *depends_on: Dependable) -> Callable[
            [Callable[['Cleaned'], T]], 'CleanedProperty[T]']:
        def func(clean: Callable[[Cleaned], T]) -> CleanedProperty[T]:
            return CleanedProperty(clean, [self, *depends_on], self)

        return func

    def constraint(self, *depends_on: Dependable) -> Callable[
            [Callable[['Cleaned'], None]], 'Constraint']:
        def func(clean: Callable[[Cleaned], None]) -> Constraint:
            return Constraint(clean, [self, *depends_on], self)

        return func


class OptionalField(Field[Optional[VT]]):
    field: Field[VT]

    def __init__(self, field: Field[VT]):
        self.field = field

    def convert(self, value: Any) -> Optional[VT]:
        if value is None:
            return None
        return self.field.convert(value)

    def validate(self, value: Optional[VT]):
        if value is not None:
            self.field.validate(value)


class CleanedProperty(Dependable[T]):
    _depends_on_cache: Optional[Set[str]] = None

    def __init__(self,
                 clean: Callable[..., T],
                 depends_on: List[Dependable],
                 field: Optional[Field] = None):
        self.clean = clean
        self.depends_on = depends_on
        self.key = (lambda: field._propname) if field else None

    def depends_on_propnames(self) -> Set[str]:
        if self._depends_on_cache is None:
            self._depends_on_cache = set(self._iterate_depends_on())
        return self._depends_on_cache

    def _iterate_depends_on(self) -> Iterable[str]:
        for d in self.depends_on:
            if isinstance(d, CleanedProperty):
                yield from d._iterate_depends_on()
            yield d._propname


class Constraint(CleanedProperty[None]):
    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        raise ConstraintAccess(
            'You can not access to constraint as property '
            f'(name: `{self._propname}`)')


class CleanedMeta:
    def __init__(self,
                 fields: Dict[str, Field],
                 cleaned_properties: Dict[str, CleanedProperty]) -> None:
        self._fields = fields
        self._cleaned_properties = cleaned_properties

    def __copy__(self):
        return CleanedMeta(self.fields, self._cleaned_properties)

    @property
    def fields(self) -> Dict[str, Field]:
        return self._fields.copy()

    @property
    def cleaned_properties(self) -> Dict[str, CleanedProperty]:
        return self._cleaned_properties.copy()


class CleanedBuilder(type):
    def __new__(cls, name: str, bases: Tuple, fields: Dict[str, Any]):
        cleaned_fields: Dict[str, Field] = dict()
        cleaned_properties: Dict[str, CleanedProperty] = dict()
        for base in bases:
            base_meta = getattr(base, '_meta', None)
            if base_meta:
                for k, v in base_meta._fields.items():
                    cleaned_fields[k] = v
                for k, v in base_meta._cleaned_properties.items():
                    cleaned_properties[k] = v

        for key, value in fields.items():
            if isinstance(value, (Field, CleanedProperty)):
                assert key not in cleaned_fields\
                    and key not in cleaned_properties,\
                    'Overriding cleaned\'s attributes should be avoided. '\
                    'Cleaned: {} propname: {}'.format(name, key)
                if isinstance(value, Field):
                    cleaned_fields[key] = value
                else:
                    cleaned_properties[key] = value

        fields['_meta'] = CleanedMeta(cleaned_fields, cleaned_properties)
        return type.__new__(cls, name, bases, fields)


class Cleaned(metaclass=CleanedBuilder):
    class Error(ValidationError):
        pass

    _meta: CleanedMeta
    _data: Dict[str, Any]

    def __init__(self, **kwargs) -> None:
        data = dict()

        unnamed_errors: Optional[List[ValidationError]] = None
        errors: Dict[str, ValidationError] = dict()

        for key, field in self._meta._fields.items():
            try:
                data[key] = field.clean(kwargs.get(key, _UNDEFINED))
            except ValidationError as e:
                errors[key] = e

        for key, cl_prop in self._meta._cleaned_properties.items():
            depends_on = cl_prop.depends_on_propnames()
            self._data = {
                propname: data[propname]
                for propname in depends_on
                if propname in data
            }
            if len(self._data) != len(depends_on):
                # skip the cleaned property
                # because the dependencies are not satisfied
                continue

            try:
                data[key] = cl_prop.clean(self)
            except DirtyFieldAccess as e:
                clsname = cl_prop.__class__.__name__
                raise AssertionError(
                    f'{clsname} `{key}` accessed to `{e.key}` during '
                    f'processing but the {clsname} is not set to depends on '
                    f'`{e.key}`. If the access is not mistake, you should '
                    f'make the {clsname} depends on `{e.key}`.') from e
            except ValidationError as e:
                if cl_prop.key:
                    errors[cl_prop.key()] = e
                else:
                    if unnamed_errors is None:
                        unnamed_errors = []
                    unnamed_errors.append(e)

        for key, cl_prop in self._meta._cleaned_properties.items():
            if isinstance(cl_prop, Constraint):
                data.pop(key, None)

        if unnamed_errors or errors:
            items: List[ValidationError.Item] = []
            if unnamed_errors:
                for err in unnamed_errors:
                    items.extend(err.items)
                    errors.update(err.nested)
            raise ValidationError(items, errors)

        self._data = data

    def __repr__(self) -> str:
        data = ', '.join('{}: {}'.format(
            k, getattr(self, k)) for k in self._meta._fields)
        return '<{}.{} ({}) at {}>'.format(
            self.__module__, self.__class__.__qualname__, data, id(self))

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._data)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Cleaned):
            return False
        return self._data == other._data


def cleaned_property(*depends_on: Dependable) -> Callable[
        [Callable[['Cleaned'], T]], 'CleanedProperty[T]']:
    def func(clean: Callable[[Cleaned], T]) -> CleanedProperty[T]:
        return CleanedProperty(clean, list(depends_on))

    return func


def constraint(*depends_on: Dependable) -> Callable[
        [Callable[['Cleaned'], None]], 'Constraint']:
    def func(clean: Callable[[Cleaned], None]) -> Constraint:
        return Constraint(clean, list(depends_on))

    return func
