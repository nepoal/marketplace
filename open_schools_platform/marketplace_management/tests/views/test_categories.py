from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from open_schools_platform.marketplace_management.tests.utils import create_test_category

NS = "api:marketplace-management:marketplace"


class CategoryListApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse(f"{NS}:marketplace-categories")

    def test_returns_empty_list(self):
        response = self.client.get(self.url)
        self.assertEqual(200, response.status_code)
        self.assertEqual(0, len(response.data["categories"]))

    def test_returns_all_categories(self):
        create_test_category(name="Education")
        create_test_category(name="Tools")
        response = self.client.get(self.url)
        self.assertEqual(200, response.status_code)
        self.assertEqual(2, len(response.data["categories"]))

    def test_anonymous_access_allowed(self):
        response = self.client.get(self.url)
        self.assertEqual(200, response.status_code)

    def test_response_contains_id_and_name(self):
        create_test_category(name="Finance")
        response = self.client.get(self.url)
        category = response.data["categories"][0]
        self.assertIn("id", category)
        self.assertIn("name", category)
        self.assertEqual("Finance", category["name"])
