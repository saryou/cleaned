from datetime import date, time
from unittest import TestCase

from cleaned.fields import StrField, IntField, BoolField, EitherField, TimeField, DateField, DictField
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
        blankable2 = StrField(blank=True, min_length=2)
        blankable2.clean('')
        with self.assertRaises(ValidationError) as ctx:
            blankable2.clean('aaa')


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
