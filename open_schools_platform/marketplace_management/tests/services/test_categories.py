from django.test import TestCase

from open_schools_platform.marketplace_management.tests.utils import create_test_category


class CreateCategoryTests(TestCase):
    def test_successful_creation(self):
        category = create_test_category(name="Education")
        self.assertEqual("Education", category.name)

    def test_duplicate_name_raises_error(self):
        create_test_category(name="Unique")
        with self.assertRaises(Exception):
            create_test_category(name="Unique")
