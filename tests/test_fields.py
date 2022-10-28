import re
from datetime import date, time
from enum import Enum
from unittest import TestCase

from cleaned.base import Cleaned, TagField, TaggedUnion
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
            dt_or_t.clean('0000-00-00')

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
    def test_spec_for_cleaned(self):
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

    def test_spec_for_tagged_union(self):
        class A(Cleaned):
            tag = TagField('a')
            one = IntField(lte=1)
            two = IntField(lte=2)

        class B(Cleaned):
            tag = TagField('b')
            one = IntField(lte=1)

        class C(Cleaned):
            tag = TagField('c')
            two = IntField(lte=2)

        class DE(Cleaned):
            tag = TagField('d', 'e')
            three = IntField(lte=3)

        u = NestedField(TaggedUnion('tag', A, B, C, DE))

        u_a = u.clean(dict(tag='a', one=1, two=2))
        self.assertIsInstance(u_a, A)
        assert isinstance(u_a, A)
        self.assertEqual(u_a.one, 1)
        self.assertEqual(u_a.two, 2)

        with self.assertRaises(ValidationError) as ctx:
            u.clean(dict(tag='a', one=2, two=2))
        self.assertIn('one', ctx.exception.nested)
        self.assertNotIn('two', ctx.exception.nested)

        with self.assertRaises(ValidationError) as ctx:
            u.clean(dict(tag='a'))
        self.assertIn('one', ctx.exception.nested)
        self.assertIn('two', ctx.exception.nested)

        # two does not exists in B
        u_b = u.clean(dict(tag='b', one=1, two=3))
        self.assertIsInstance(u_b, B)
        assert isinstance(u_b, B)
        self.assertEqual(u_b.one, 1)

        # one does not exists in C
        u_c = u.clean(dict(tag='c', one=3, two=2))
        self.assertIsInstance(u_c, C)
        assert isinstance(u_c, C)
        self.assertEqual(u_c.two, 2)

        u_de = u.clean(dict(tag='d', three=3))
        self.assertIsInstance(u_de, DE)
        assert isinstance(u_de, DE)
        self.assertEqual(u_de.three, 3)

        u_de = u.clean(dict(tag='e', three=2))
        self.assertIsInstance(u_de, DE)
        assert isinstance(u_de, DE)
        self.assertEqual(u_de.three, 2)

        with self.assertRaises(ValidationError) as ctx:
            u.clean(dict(tag='f'))
        self.assertEqual(len(ctx.exception.items), 1)
        self.assertEqual(len(ctx.exception.nested), 0)
