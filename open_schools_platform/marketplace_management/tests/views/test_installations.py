import uuid

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from open_schools_platform.marketplace_management.models import App, Installation
from open_schools_platform.marketplace_management.services.app import install_app
from open_schools_platform.marketplace_management.tests.utils import (
    create_test_app,
    create_test_installation,
    create_test_paid_app,
    create_test_payment,
)
from open_schools_platform.user_management.users.tests.utils import (
    create_logged_in_user,
    create_test_user,
)

NS = "api:marketplace-management:marketplace"


class AppInstallApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = lambda pk: reverse(f"{NS}:marketplace-apps-install", args=[pk])

    def test_successful_installation(self):
        create_logged_in_user(instance=self)
        app = create_test_app()
        response = self.client.post(self.url(app.id))
        self.assertEqual(201, response.status_code)
        self.assertEqual(1, Installation.objects.count())

    def test_response_contains_installation(self):
        create_logged_in_user(instance=self)
        app = create_test_app()
        response = self.client.post(self.url(app.id))
        self.assertIn("installation", response.data)
        self.assertTrue(response.data["installation"]["active"])

    def test_unauthorized_returns_401(self):
        app = create_test_app()
        response = self.client.post(self.url(app.id))
        self.assertEqual(401, response.status_code)

    def test_app_not_found_returns_404(self):
        create_logged_in_user(instance=self)
        response = self.client.post(self.url(uuid.uuid4()))
        self.assertEqual(404, response.status_code)

    def test_inactive_app_returns_400(self):
        create_logged_in_user(instance=self)
        pending_app = create_test_app(status=App.Status.PENDING)
        response = self.client.post(self.url(pending_app.id))
        self.assertEqual(400, response.status_code)

    def test_paid_app_without_payment_returns_400(self):
        create_logged_in_user(instance=self)
        paid_app = create_test_paid_app()
        response = self.client.post(self.url(paid_app.id))
        self.assertEqual(400, response.status_code)

    def test_paid_app_with_payment_returns_201(self):
        user = create_logged_in_user(instance=self)
        paid_app = create_test_paid_app()
        create_test_payment(app=paid_app, user=user)
        response = self.client.post(self.url(paid_app.id))
        self.assertEqual(201, response.status_code)

    def test_already_installed_returns_400(self):
        user = create_logged_in_user(instance=self)
        app = create_test_app()
        install_app(app=app, user=user)
        response = self.client.post(self.url(app.id))
        self.assertEqual(400, response.status_code)


class AppUninstallApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = lambda pk: reverse(f"{NS}:marketplace-apps-uninstall", args=[pk])

    def test_successful_uninstall(self):
        user = create_logged_in_user(instance=self)
        app = create_test_app()
        install_app(app=app, user=user)
        response = self.client.delete(self.url(app.id))
        self.assertEqual(204, response.status_code)
        installation = Installation.objects.get(app=app, user=user)
        self.assertFalse(installation.active)

    def test_unauthorized_returns_401(self):
        app = create_test_app()
        response = self.client.delete(self.url(app.id))
        self.assertEqual(401, response.status_code)

    def test_not_installed_returns_400(self):
        create_logged_in_user(instance=self)
        app = create_test_app()
        response = self.client.delete(self.url(app.id))
        self.assertEqual(400, response.status_code)

    def test_app_not_found_returns_404(self):
        create_logged_in_user(instance=self)
        response = self.client.delete(self.url(uuid.uuid4()))
        self.assertEqual(404, response.status_code)


class UserInstallationListApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse(f"{NS}:marketplace-my-installations")

    def test_returns_user_installations(self):
        user = create_logged_in_user(instance=self)
        app = create_test_app()
        install_app(app=app, user=user)
        response = self.client.get(self.url)
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, response.data["count"])

    def test_unauthorized_returns_401(self):
        response = self.client.get(self.url)
        self.assertEqual(401, response.status_code)

    def test_does_not_return_other_users_installations(self):
        create_logged_in_user(instance=self)
        other_user = create_test_user(phone="+79999999999")
        app = create_test_app()
        create_test_installation(app=app, user=other_user)
        response = self.client.get(self.url)
        self.assertEqual(200, response.status_code)
        self.assertEqual(0, response.data["count"])

    def test_returns_empty_for_user_with_no_installations(self):
        create_logged_in_user(instance=self)
        response = self.client.get(self.url)
        self.assertEqual(200, response.status_code)
        self.assertEqual(0, response.data["count"])
