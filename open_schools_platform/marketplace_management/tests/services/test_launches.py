from django.test import TestCase
from rest_framework.exceptions import ValidationError

from open_schools_platform.marketplace_management.models import App, Installation
from open_schools_platform.marketplace_management.services.app import (
    build_launch_url,
    create_app_launch,
    install_app,
)
from open_schools_platform.marketplace_management.tests.utils import (
    create_test_app,
    create_test_app_launch,
)
from open_schools_platform.user_management.users.tests.utils import create_test_user


class CreateAppLaunchTests(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.app = create_test_app(with_url=True)
        install_app(app=self.app, user=self.user)

    def test_successful_launch_creation(self):
        launch = create_app_launch(app=self.app, user=self.user)
        self.assertFalse(launch.is_expired)
        self.assertFalse(launch.is_used)
        self.assertTrue(len(launch.launch_token) > 0)

    def test_launch_inactive_app_raises_error(self):
        pending_app = create_test_app(name="Pending", status=App.Status.PENDING, with_url=True)
        Installation.objects.create_installation(app=pending_app, user=self.user)
        with self.assertRaises(ValidationError):
            create_app_launch(app=pending_app, user=self.user)

    def test_launch_without_installation_raises_error(self):
        other_user = create_test_user(phone="+79999999999")
        with self.assertRaises(ValidationError):
            create_app_launch(app=self.app, user=other_user)

    def test_multiple_launches_can_be_created(self):
        create_app_launch(app=self.app, user=self.user)
        create_app_launch(app=self.app, user=self.user)
        self.assertEqual(2, self.app.launches.count())


class BuildLaunchUrlTests(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.app = create_test_app(with_url=True)
        install_app(app=self.app, user=self.user)

    def test_launch_url_contains_user_id_and_token(self):
        launch = create_app_launch(app=self.app, user=self.user)
        url = build_launch_url(app_launch=launch)
        self.assertIn(str(self.user.id), url)
        self.assertIn(launch.launch_token, url)
        self.assertIn("platform_user_id=", url)
        self.assertIn("launch_token=", url)

    def test_launch_url_uses_app_base_url(self):
        launch = create_app_launch(app=self.app, user=self.user)
        url = build_launch_url(app_launch=launch)
        self.assertIn("https://testapp.example.com", url)

    def test_launch_url_without_url_config_raises_error(self):
        app_no_url = create_test_app(name="No URL App")
        install_app(app=app_no_url, user=self.user)
        launch = create_test_app_launch(app=app_no_url, user=self.user)
        with self.assertRaises(ValidationError):
            build_launch_url(app_launch=launch)
