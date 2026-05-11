import uuid

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from open_schools_platform.marketplace_management.models import App, Installation
from open_schools_platform.marketplace_management.services.app import install_app
from open_schools_platform.marketplace_management.tests.utils import create_test_app
from open_schools_platform.user_management.users.tests.utils import create_logged_in_user

NS = "api:marketplace-management:marketplace"


class AppLaunchApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = lambda pk: reverse(f"{NS}:marketplace-apps-launch", args=[pk])

    def test_successful_launch(self):
        user = create_logged_in_user(instance=self)
        app = create_test_app(with_url=True)
        install_app(app=app, user=user)
        response = self.client.get(self.url(app.id))
        self.assertEqual(200, response.status_code)
        self.assertIn("launch_url", response.data)
        self.assertIn("launch_token", response.data)
        self.assertIn("expires_at", response.data)

    def test_launch_url_contains_platform_user_id(self):
        user = create_logged_in_user(instance=self)
        app = create_test_app(with_url=True)
        install_app(app=app, user=user)
        response = self.client.get(self.url(app.id))
        self.assertIn(str(user.id), response.data["launch_url"])

    def test_unauthorized_returns_401(self):
        app = create_test_app(with_url=True)
        response = self.client.get(self.url(app.id))
        self.assertEqual(401, response.status_code)

    def test_not_installed_returns_400(self):
        create_logged_in_user(instance=self)
        app = create_test_app(with_url=True)
        response = self.client.get(self.url(app.id))
        self.assertEqual(400, response.status_code)

    def test_inactive_app_returns_400(self):
        user = create_logged_in_user(instance=self)
        pending_app = create_test_app(name="Pending", status=App.Status.PENDING, with_url=True)
        Installation.objects.create_installation(app=pending_app, user=user)
        response = self.client.get(self.url(pending_app.id))
        self.assertEqual(400, response.status_code)

    def test_app_not_found_returns_404(self):
        create_logged_in_user(instance=self)
        response = self.client.get(self.url(uuid.uuid4()))
        self.assertEqual(404, response.status_code)
