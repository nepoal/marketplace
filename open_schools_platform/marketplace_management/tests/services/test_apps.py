from decimal import Decimal

from django.test import TestCase

from open_schools_platform.marketplace_management.models import App
from open_schools_platform.marketplace_management.services.app import create_app
from open_schools_platform.marketplace_management.tests.utils import (
    create_test_app,
    create_test_paid_app,
)


class CreateAppTests(TestCase):
    def test_free_app_creation(self):
        app = create_test_app()
        self.assertTrue(app.is_free)
        self.assertIsNone(app.amount)

    def test_paid_app_creation(self):
        app = create_test_paid_app(amount=Decimal("199.00"))
        self.assertFalse(app.is_free)
        self.assertEqual(Decimal("199.00"), app.amount)

    def test_paid_app_without_amount_raises_error(self):
        with self.assertRaises(Exception):
            create_app(name="Bad Paid App", is_free=False, amount=None)

    def test_app_default_status_is_pending(self):
        app = create_app(name="Draft App")
        self.assertEqual(App.Status.PENDING, app.status)
