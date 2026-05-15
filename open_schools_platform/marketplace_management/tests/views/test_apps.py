import uuid

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from open_schools_platform.marketplace_management.tests.utils import (
    create_test_app,
    create_test_app_version,
)
from open_schools_platform.user_management.users.tests.utils import create_logged_in_user

NS = "api:marketplace-management:marketplace"


class AppListApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse(f"{NS}:marketplace-apps-list")

    def test_returns_paginated_list(self):
        create_logged_in_user(instance=self)
        create_test_app(name="App Alpha")
        create_test_app(name="App Beta")
        response = self.client.get(self.url)
        self.assertEqual(200, response.status_code)
        self.assertEqual(2, response.data["count"])

    def test_unauthorized_returns_401(self):
        response = self.client.get(self.url)
        self.assertEqual(401, response.status_code)

    def test_filter_by_name(self):
        create_logged_in_user(instance=self)
        create_test_app(name="Unique App Name")
        create_test_app(name="Another App")
        response = self.client.get(self.url, {"name": "Unique App Name"})
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, response.data["count"])

    def test_response_fields(self):
        create_logged_in_user(instance=self)
        create_test_app(name="Test")
        response = self.client.get(self.url)
        app_data = response.data["results"][0]
        for field in (
            "id",
            "name",
            "status",
            "is_free",
            "categories",
            "average_rating",
        ):
            self.assertIn(field, app_data)


class AppDetailApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = lambda pk: reverse(f"{NS}:marketplace-apps-detail", args=[pk])

    def test_successful_get(self):
        create_logged_in_user(instance=self)
        app = create_test_app()
        response = self.client.get(self.url(app.id))
        self.assertEqual(200, response.status_code)
        self.assertEqual(str(app.id), response.data["app"]["id"])

    def test_not_found_returns_404(self):
        create_logged_in_user(instance=self)
        response = self.client.get(self.url(uuid.uuid4()))
        self.assertEqual(404, response.status_code)

    def test_unauthorized_returns_401(self):
        app = create_test_app()
        response = self.client.get(self.url(app.id))
        self.assertEqual(401, response.status_code)

    def test_detail_includes_latest_version(self):
        create_logged_in_user(instance=self)
        app = create_test_app()
        create_test_app_version(app=app, version="2.0.0")
        response = self.client.get(self.url(app.id))
        self.assertIsNotNone(response.data["app"]["latest_version"])
        self.assertEqual("2.0.0", response.data["app"]["latest_version"]["version"])

    def test_detail_without_version_returns_null(self):
        create_logged_in_user(instance=self)
        app = create_test_app()
        response = self.client.get(self.url(app.id))
        self.assertIsNone(response.data["app"]["latest_version"])
