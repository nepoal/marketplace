import uuid

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from open_schools_platform.marketplace_management.tests.utils import (
    create_test_app,
    create_test_paid_app,
    create_test_payment,
)
from open_schools_platform.user_management.users.tests.utils import (
    create_logged_in_user,
)

NS = "api:marketplace-management:marketplace"


class AppPayApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = lambda pk: reverse(f"{NS}:marketplace-apps-pay", args=[pk])

    def test_successful_payment(self):
        create_logged_in_user(instance=self)
        paid_app = create_test_paid_app()
        response = self.client.post(self.url(paid_app.id))
        self.assertEqual(201, response.status_code)
        for field in ("id", "amount", "currency", "status"):
            self.assertIn(field, response.data)

    def test_unauthorized_returns_401(self):
        paid_app = create_test_paid_app()
        response = self.client.post(self.url(paid_app.id))
        self.assertEqual(401, response.status_code)

    def test_free_app_returns_400(self):
        create_logged_in_user(instance=self)
        free_app = create_test_app()
        response = self.client.post(self.url(free_app.id))
        self.assertEqual(400, response.status_code)

    def test_duplicate_payment_returns_400(self):
        user = create_logged_in_user(instance=self)
        paid_app = create_test_paid_app()
        create_test_payment(app=paid_app, user=user)
        response = self.client.post(self.url(paid_app.id))
        self.assertEqual(400, response.status_code)

    def test_app_not_found_returns_404(self):
        create_logged_in_user(instance=self)
        response = self.client.post(self.url(uuid.uuid4()))
        self.assertEqual(404, response.status_code)
