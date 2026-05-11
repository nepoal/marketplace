from django.test import TestCase
from rest_framework.exceptions import ValidationError

from open_schools_platform.marketplace_management.models import App, Installation
from open_schools_platform.marketplace_management.services.app import install_app, uninstall_app
from open_schools_platform.marketplace_management.tests.utils import (
    create_test_app,
    create_test_paid_app,
    create_test_payment,
)
from open_schools_platform.user_management.users.tests.utils import create_test_user


class InstallAppTests(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.app = create_test_app()

    def test_successful_installation(self):
        installation = install_app(app=self.app, user=self.user)
        self.assertTrue(installation.active)
        self.assertEqual(1, Installation.objects.count())

    def test_install_pending_app_raises_error(self):
        pending_app = create_test_app(name="Pending", status=App.Status.PENDING)
        with self.assertRaises(ValidationError):
            install_app(app=pending_app, user=self.user)

    def test_install_suspended_app_raises_error(self):
        suspended_app = create_test_app(name="Suspended", status=App.Status.SUSPENDED)
        with self.assertRaises(ValidationError):
            install_app(app=suspended_app, user=self.user)

    def test_install_already_installed_raises_error(self):
        install_app(app=self.app, user=self.user)
        with self.assertRaises(ValidationError):
            install_app(app=self.app, user=self.user)

    def test_install_paid_app_without_payment_raises_error(self):
        paid_app = create_test_paid_app()
        with self.assertRaises(ValidationError):
            install_app(app=paid_app, user=self.user)

    def test_install_paid_app_with_completed_payment_succeeds(self):
        paid_app = create_test_paid_app()
        create_test_payment(app=paid_app, user=self.user)
        installation = install_app(app=paid_app, user=self.user)
        self.assertTrue(installation.active)
        self.assertIsNotNone(installation.payment)

    def test_reinstall_after_uninstall_restores_same_record(self):
        install_app(app=self.app, user=self.user)
        uninstall_app(app=self.app, user=self.user)
        installation = install_app(app=self.app, user=self.user)
        self.assertTrue(installation.active)
        self.assertEqual(1, Installation.objects.count())


class UninstallAppTests(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.app = create_test_app()

    def test_successful_uninstall(self):
        install_app(app=self.app, user=self.user)
        uninstall_app(app=self.app, user=self.user)
        installation = Installation.objects.get(app=self.app, user=self.user)
        self.assertFalse(installation.active)

    def test_uninstall_not_installed_raises_error(self):
        with self.assertRaises(ValidationError):
            uninstall_app(app=self.app, user=self.user)
