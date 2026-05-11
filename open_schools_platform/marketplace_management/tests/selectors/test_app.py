import uuid

from django.test import TestCase

from open_schools_platform.marketplace_management.selectors.app import (
    get_app,
    get_app_launch,
    get_apps,
    get_categories,
    get_category,
)
from open_schools_platform.marketplace_management.tests.utils import (
    create_test_app,
    create_test_app_launch,
    create_test_category,
)
from open_schools_platform.user_management.users.tests.utils import create_test_user


class GetAppSelectorTests(TestCase):
    def test_get_app_by_id(self):
        app = create_test_app()
        result = get_app(filters={"id": app.id})
        self.assertEqual(app, result)

    def test_get_app_nonexistent_returns_none(self):
        result = get_app(filters={"id": uuid.uuid4()})
        self.assertIsNone(result)

    def test_get_apps_returns_queryset(self):
        create_test_app(name="App 1")
        create_test_app(name="App 2")
        result = get_apps()
        self.assertEqual(2, result.count())


class GetAppLaunchSelectorTests(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.app = create_test_app(with_url=True)
        self.launch = create_test_app_launch(app=self.app, user=self.user)

    def test_get_by_launch_token(self):
        result = get_app_launch(filters={"launch_token": self.launch.launch_token})
        self.assertEqual(self.launch, result)

    def test_get_by_id(self):
        result = get_app_launch(filters={"id": self.launch.id})
        self.assertEqual(self.launch, result)

    def test_nonexistent_returns_none(self):
        result = get_app_launch(filters={"launch_token": "nonexistent-token"})
        self.assertIsNone(result)


class GetCategorySelectorTests(TestCase):
    def setUp(self):
        self.category = create_test_category(name="Education")

    def test_get_by_id(self):
        result = get_category(filters={"id": self.category.id})
        self.assertEqual(self.category, result)

    def test_get_by_name(self):
        result = get_category(filters={"name": "Education"})
        self.assertEqual(self.category, result)

    def test_nonexistent_returns_none(self):
        result = get_category(filters={"id": uuid.uuid4()})
        self.assertIsNone(result)

    def test_get_categories_returns_all(self):
        create_test_category(name="Science")
        result = get_categories()
        self.assertEqual(2, result.count())
