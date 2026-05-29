from django.test import TestCase
from rest_framework.exceptions import ValidationError

from open_schools_platform.marketplace_management.models import Payment
from open_schools_platform.marketplace_management.services.app import create_payment
from open_schools_platform.marketplace_management.tests.utils import (
    create_test_app,
    create_test_paid_app,
    create_test_payment,
)
from open_schools_platform.user_management.users.tests.utils import create_test_user


class CreatePaymentTests(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.paid_app = create_test_paid_app()

    def test_successful_payment_creation(self):
        payment = create_payment(app=self.paid_app, user=self.user)
        self.assertEqual(Payment.Status.COMPLETED, payment.status)
        self.assertEqual(self.paid_app.amount, payment.amount)
        self.assertEqual(self.paid_app.currency, payment.currency)

    def test_payment_for_free_app_raises_error(self):
        free_app = create_test_app()
        with self.assertRaises(ValidationError):
            create_payment(app=free_app, user=self.user)

    def test_duplicate_completed_payment_raises_error(self):
        create_test_payment(app=self.paid_app, user=self.user)
        with self.assertRaises(ValidationError):
            create_payment(app=self.paid_app, user=self.user)
