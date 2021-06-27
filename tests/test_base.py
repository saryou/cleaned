from unittest import TestCase

from cleaned.base import Cleaned, OptionalField
from cleaned.fields import IntField
from cleaned.errors import ValidationError


class OptionalFieldTests(TestCase):
    def test_spec(self):
        field = IntField().opt()
        self.assertIsInstance(field, OptionalField)
        self.assertIsNone(field.convert(None))
        self.assertIsNone(field.clean(None))

        class C1(Cleaned):
            a = IntField().opt()

        with self.assertRaises(ValidationError):
            C1()

        class C2(Cleaned):
            a = IntField().default(1).opt()

        with self.assertRaises(ValidationError):
            C2()

        class C3(Cleaned):
            a = IntField().opt().default(None)

        self.assertIsNone(C3().a)
