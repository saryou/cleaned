from datetime import date
from unittest import TestCase

from cleaned.fields import StrField, IntField, DateField, DictField
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
