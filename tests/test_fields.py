import re
from datetime import date, time
from enum import Enum
from unittest import TestCase

from cleaned.base import Cleaned
from cleaned.fields import StrField, IntField, BoolField, EitherField, TimeField, DateField, SetField, DictField, EnumField, NestedField
from cleaned.errors import ValidationError, ErrorCode


class StrFieldTests(TestCase):
    def test_blank(self):
        blankable = StrField(blank=True)
        not_blankable = StrField(blank=False)

        blankable.convert('')
        not_blankable.convert('')

        blankable.validate('')
        with self.assertRaises(ValidationError) as ctx:
            not_blankable.clean('')
        with self.assertRaises(ValidationError) as ctx:
            not_blankable.clean('   \n \t ')
        self.assertIn(ErrorCode.blank, ctx.exception.to_flat_codes())

        # skip validations for empty value
        blankable2 = StrField(blank=True, max_length=2)
        blankable2.clean('')
        with self.assertRaises(ValidationError) as ctx:
            blankable2.clean('aaa')

        pattern = r'^\d+$'
        regex_field = StrField(blank=False, pattern=pattern)
        regex_field.clean('5')
        with self.assertRaises(ValidationError) as ctx:
            regex_field.clean('a5')
        self.assertEqual(regex_field.raw_pattern, pattern)
        self.assertEqual(regex_field.pattern, re.compile(pattern))


class EitherFieldTests(TestCase):
    def test_spec(self):
        dt_or_t = EitherField(DateField(), TimeField())
        self.assertEqual(dt_or_t.clean('2000-01-01'), date(2000, 1, 1))
        self.assertEqual(dt_or_t.clean('10:00:00'), time(10, 0, 0))
        with self.assertRaises(ValidationError):
            dt_or_t.clean('000000')

        i_or_b = EitherField(IntField(), BoolField())
        # t1 is priority
        self.assertEqual(i_or_b.clean(True), 1)
        self.assertEqual(i_or_b.clean('a'), True)
        self.assertEqual(i_or_b.clean(''), False)


class SetFieldTests(TestCase):
    def test_spec(self):
        field = SetField(IntField())

        self.assertEqual(field.clean('["1", "2", "2", "3"]'), {1, 2, 3})
        self.assertEqual(field.clean([1, 2, 3, 3]), {1, 2, 3})

        with self.assertRaises(ValidationError) as ctx:
            field.clean(['a', 'b', 'c', 'c'])
        self.assertEqual(len(ctx.exception.items), 4)
        self.assertEqual(len(ctx.exception.nested), 0)


class DictFieldTests(TestCase):
    def test_default_key_field(self):
        # default key is StrField
        field = DictField(IntField())
        self.assertIsInstance(field.value, IntField)
        self.assertIsInstance(field.key, StrField)

    def test_specs(self):
        field = DictField(DateField(), IntField())
        self.assertIsInstance(field.value, DateField)
        self.assertIsInstance(field.key, IntField)

        # json
        self.assertEqual(
            field.clean('{"1": "2000-01-01", "2": "1999-12-31"}'),
            {1: date(2000, 1, 1), 2: date(1999, 12, 31)})

        # dict
        self.assertEqual(
            field.clean({'1': '2000-01-01', '2': '1999-12-31'}),
            {1: date(2000, 1, 1), 2: date(1999, 12, 31)})

        with self.assertRaises(ValidationError) as ctx:
            field.clean({'a': 'b'})
        self.assertEqual(len(ctx.exception.items), 0)
        self.assertEqual(len(ctx.exception.nested), 2)
        # key error
        self.assertIn('a:key', ctx.exception.nested)
        # value error
        self.assertIn('a', ctx.exception.nested)


class EnumFieldTests(TestCase):
    def test_specs(self):
        class Result(Enum):
            ok = 1
            ng = 0

        field = EnumField(Result)

        self.assertEqual(field.clean(Result.ok), Result.ok)
        self.assertEqual(field.clean(1), Result.ok)
        self.assertEqual(field.clean('ok'), Result.ok)

        self.assertEqual(field.clean(Result.ng), Result.ng)
        self.assertEqual(field.clean(0), Result.ng)
        self.assertEqual(field.clean('ng'), Result.ng)

        with self.assertRaises(ValidationError):
            field.clean('1')


class NestedFieldTests(TestCase):
    def test_specs(self):
        class Nested(Cleaned):
            a = IntField()

        field = NestedField(Nested)

        nested = Nested(a=1)

        # json
        self.assertEqual(field.clean('{"a": "1"}'), nested)
        # dict
        self.assertEqual(field.clean({'a': '1'}), nested)
        # cleaned
        self.assertEqual(field.clean(Nested(a=1)), nested)

        with self.assertRaises(ValidationError) as ctx:
            field.clean({'a': 'a'})

        self.assertEqual(len(ctx.exception.items), 0)
        self.assertEqual(len(ctx.exception.nested), 1)
        self.assertIn('a', ctx.exception.nested)
