from unittest import TestCase
from unittest.mock import patch

from cleaned.base import Cleaned, OptionalField, cleaned_property, constraint, ConstraintAccess, TagField, TaggedUnion
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

        class C4(Cleaned):
            value = IntField()
            max = IntField()
            min = IntField()

            @value.cleaned_property(max, min)
            def twice_as_value(self) -> int:
                if self.value * 2 > self.max:
                    raise self.Error('must be value * 2 <= max')
                if self.value * 2 < self.min:
                    raise self.Error('must be value * 2 >= min')
                return self.value * 2

        with self.assertRaises(ValidationError) as ctx:
            C4(value=1, max=1)
        # cleaned_property was not evaluated because min,
        # which is a dependency, was not satisfied.
        self.assertNotIn('value', ctx.exception.nested)
        self.assertNotIn('max', ctx.exception.nested)
        self.assertIn('min', ctx.exception.nested)

        with self.assertRaises(ValidationError) as ctx:
            C4(value=1, max=1, min=1)
        self.assertIn('value', ctx.exception.nested)
        self.assertNotIn('max', ctx.exception.nested)
        self.assertNotIn('min', ctx.exception.nested)

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


class TagFieldTests(TestCase):
    def test_spec(self):
        a = TagField('a')
        self.assertEqual(a.clean('a'), 'a')
        one_or_two = TagField('1', '2')
        self.assertEqual(one_or_two.clean('1'), '1')
        self.assertEqual(one_or_two.clean('2'), '2')

        with self.assertRaises(ValidationError):
            one_or_two.clean(1)
        with self.assertRaises(ValidationError):
            one_or_two.clean(2)

        # at least one tag is required
        with self.assertRaises(AssertionError):
            TagField()

        # all tags must be str
        with self.assertRaises(AssertionError):
            TagField(1)  # type: ignore
        with self.assertRaises(AssertionError):
            TagField('1', 1)  # type: ignore

        # all tags must not be empty
        with self.assertRaises(AssertionError):
            TagField('')
        with self.assertRaises(AssertionError):
            TagField('a', '')

        # tags must be unique
        with self.assertRaises(AssertionError):
            TagField('a', 'a')
        with self.assertRaises(AssertionError):
            TagField('a', 'b', 'a')


class TaggedUnionTests(TestCase):
    def test_spec(self):
        class A(Cleaned):
            tag = TagField('a')
            one = IntField(lte=1)
            two = IntField(lte=2)

        class AA(A):
            pass

        class B(Cleaned):
            tag = TagField('b')
            one = IntField(lte=1)

        class C(Cleaned):
            tag = TagField('c')
            two = IntField(lte=2)

        class D(Cleaned):
            tag = TagField('d')

        class DE(Cleaned):
            tag = TagField('d', 'e')
            three = IntField(lte=3)

        class Irrelevant(Cleaned):
            other_tag_name = TagField('i')

        u = TaggedUnion('tag', A, B, C, DE)

        u_a = u(tag='a', one=1, two=2)
        self.assertIsInstance(u_a, A)
        assert isinstance(u_a, A)
        self.assertEqual(u_a.one, 1)
        self.assertEqual(u_a.two, 2)

        with self.assertRaises(ValidationError) as ctx:
            u(tag='a', one=2, two=2)
        self.assertIn('one', ctx.exception.nested)
        self.assertNotIn('two', ctx.exception.nested)

        with self.assertRaises(ValidationError) as ctx:
            u(tag='a')
        self.assertIn('one', ctx.exception.nested)
        self.assertIn('two', ctx.exception.nested)

        # two does not exists in B
        u_b = u(tag='b', one=1, two=3)
        self.assertIsInstance(u_b, B)
        assert isinstance(u_b, B)
        self.assertEqual(u_b.one, 1)

        # one does not exists in C
        u_c = u(tag='c', one=3, two=2)
        self.assertIsInstance(u_c, C)
        assert isinstance(u_c, C)
        self.assertEqual(u_c.two, 2)

        u_de = u(tag='d', three=3)
        self.assertIsInstance(u_de, DE)
        assert isinstance(u_de, DE)
        self.assertEqual(u_de.three, 3)

        u_de = u(tag='e', three=2)
        self.assertIsInstance(u_de, DE)
        assert isinstance(u_de, DE)
        self.assertEqual(u_de.three, 2)

        with self.assertRaises(TypeError) as ctx:
            u(tag='f')

        # fallback
        u2 = TaggedUnion('tag', A, B, C, fallback='a')
        # fallback only works when tag is None or unspecified
        self.assertIsInstance(u2(one=1, two=2), A)
        self.assertIsInstance(u2(tag=None, one=1, two=2), A)
        with self.assertRaises(TypeError):
            u2(tag='')
        with self.assertRaises(TypeError):
            u2(tag='_')
        # invalid fallback
        with self.assertRaises(AssertionError):
            TaggedUnion('tag', A, B, fallback='c')

        # same type member will be skipped
        self.assertEqual(TaggedUnion('tag', A, A, B).members, (A, B))

        # all members must have tag fields which have same field name
        with self.assertRaises(AssertionError):
            TaggedUnion('tag', A, Irrelevant)

        # all members must have unique tag names
        with self.assertRaises(AssertionError):
            TaggedUnion('tag', D, DE)
        with self.assertRaises(AssertionError):
            TaggedUnion('tag', A, AA)
