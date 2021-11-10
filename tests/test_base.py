from unittest import TestCase
from unittest.mock import patch

from cleaned.base import Cleaned, OptionalField, cleaned_property, constraint, ConstraintAccess
from cleaned.fields import IntField
from cleaned.errors import ValidationError
from cleaned.utils import Undefined


class FieldTests(TestCase):
    def test_clean(self):
        undefined = Undefined()

        f1 = IntField()
        with self.assertRaises(ValidationError):
            f1.clean(undefined)

        f2 = IntField().default(2)
        self.assertEqual(f2.clean(undefined), 2)

        f3 = IntField().default(lambda: 3)
        self.assertEqual(f3.clean(undefined), 3)

        f4 = IntField()
        with patch.object(f4, 'convert') as convert,\
                patch.object(f4, 'validate') as validate:
            self.assertEqual(f4.clean('4'), convert.return_value)

            convert.assert_called_once_with('4')
            validate.assert_called_once_with(convert.return_value)

    def test_describe(self):
        class C1(Cleaned):
            a = IntField().describe(label='label')
            b = IntField().describe(desc='desc')
            c = IntField().describe(label='label', desc='desc')

        self.assertEqual(C1.a.label, 'label')
        self.assertEqual(C1.a.desc, '')

        self.assertEqual(C1.b.label, '')
        self.assertEqual(C1.b.desc, 'desc')

        self.assertEqual(C1.c.label, 'label')
        self.assertEqual(C1.c.desc, 'desc')

    def test_opt(self):
        class C1(Cleaned):
            a = IntField().opt()

        self.assertIsInstance(C1.a, OptionalField)
        with self.assertRaises(ValidationError):
            C1()

        class C2(Cleaned):
            a = IntField().describe(label='a', desc='b').default(1).opt()

        self.assertIsInstance(C2.a, OptionalField)
        C2()
        self.assertEqual(C2.a.label, C2.a.field.label)
        self.assertEqual(C2.a.desc, C2.a.field.desc)

        class C3(Cleaned):
            a = IntField().opt().describe(label='a', desc='b').default(None)

        self.assertIsInstance(C3.a, OptionalField)
        self.assertIsNone(C3().a)


class OptionalFieldTests(TestCase):
    def test_spec(self):
        field = IntField().opt()
        self.assertIsInstance(field, OptionalField)
        self.assertIsNone(field.convert(None))
        self.assertIsNone(field.clean(None))


class CleanedTests(TestCase):
    def test_spec(self):
        class C(Cleaned):
            a = IntField()
            b = IntField()

        # ok
        C(a=1, b=1)

        with self.assertRaises(ValidationError) as e:
            C()
        self.assertIn('a', e.exception.nested)
        self.assertIn('b', e.exception.nested)

        with self.assertRaises(ValidationError) as e:
            C(a=1)
        self.assertNotIn('a', e.exception.nested)
        self.assertIn('b', e.exception.nested)

        with self.assertRaises(ValidationError) as e:
            C(b=1)
        self.assertIn('a', e.exception.nested)
        self.assertNotIn('b', e.exception.nested)

        with patch.object(C.a, 'clean') as clean_a,\
                patch.object(C.b, 'clean') as clean_b:
            C()
            clean_a.assert_called_once_with(Undefined())
            clean_b.assert_called_once_with(Undefined())

        self.assertEqual(C(a=1, b=2).to_dict(), dict(a=1, b=2))

        self.assertEqual(C(a=1, b=1), C(a=1, b=1))
        self.assertNotEqual(C(a=1, b=1), C(a=1, b=2))

    def test_cleaned_properties(self):
        class C1(Cleaned):
            value = IntField()
            max = IntField()

            @value.cleaned_property(max)
            def twice_as_value(self) -> int:
                if self.value * 2 > self.max:
                    raise self.Error('must be value * 2 <= max')
                return self.value * 2

        c = C1(value=1, max=3)
        self.assertEqual(c.twice_as_value, 2)
        self.assertEqual(c.to_dict(), dict(value=1, max=3, twice_as_value=2))

        with self.assertRaises(ValidationError) as ctx:
            C1(value=1, max=1)
        self.assertIn('value', ctx.exception.nested)

        class C2(Cleaned):
            value = IntField()
            max = IntField()

            @cleaned_property(value, max)
            def twice_as_value(self) -> int:
                if self.value * 2 > self.max:
                    raise self.Error('must be value * 2 <= max')
                return self.value * 2

        with self.assertRaises(ValidationError) as ctx:
            C2(value=1, max=1)
        self.assertEqual(len(ctx.exception.items), 1)
        self.assertFalse(ctx.exception.nested)

        class C3(Cleaned):
            value = IntField()
            max = IntField()

            @cleaned_property(value)
            def twice_as_value(self) -> int:
                # max is not present in depends_on
                if self.value * 2 > self.max:
                    raise self.Error('must be value * 2 <= max')
                return self.value * 2

        with self.assertRaises(AssertionError) as ctx:
            C3(value=1, max=3)

    def test_constraints(self):
        class C1(Cleaned):
            a = IntField()
            b = IntField()

            @a.constraint(b)
            def a_must_lt_b(self):
                if self.a < self.b:
                    return
                raise self.Error('a < b is not satisfied')

        c = C1(a=1, b=3)
        self.assertEqual(c.to_dict(), dict(a=1, b=3))

        with self.assertRaises(ConstraintAccess):
            c.a_must_lt_b

        with self.assertRaises(ValidationError) as ctx:
            C1(a=1, b=1)
        self.assertIn('a', ctx.exception.nested)

        class C2(Cleaned):
            a = IntField()
            b = IntField()

            @constraint(a, b)
            def a_must_lt_b(self):
                if self.a < self.b:
                    return
                raise self.Error('a < b is not satisfied')

        with self.assertRaises(ValidationError) as ctx:
            C2(a=1, b=1)
        self.assertEqual(len(ctx.exception.items), 1)
        self.assertFalse(ctx.exception.nested)
