from django.test import TestCase

from open_schools_platform.marketplace_management.selectors.marketplace import (
    get_installation,
    get_installations,
    get_review,
    get_reviews,
    get_user_installation,
    get_user_review,
)
from open_schools_platform.marketplace_management.tests.utils import (
    create_test_app,
    create_test_installation,
    create_test_review,
)
from open_schools_platform.user_management.users.tests.utils import create_test_user


class GetUserReviewSelectorTests(TestCase):
    def test_returns_existing_review(self):
        user = create_test_user()
        app = create_test_app()
        review = create_test_review(app=app, user=user, rating=4)
        result = get_user_review(user=user, app=app)
        self.assertEqual(review, result)

    def test_returns_none_when_no_review(self):
        user = create_test_user()
        app = create_test_app()
        result = get_user_review(user=user, app=app)
        self.assertIsNone(result)


class GetUserInstallationSelectorTests(TestCase):
    def test_returns_existing_installation(self):
        user = create_test_user()
        app = create_test_app()
        installation = create_test_installation(app=app, user=user)
        result = get_user_installation(user=user, app=app)
        self.assertEqual(installation, result)

    def test_returns_none_when_not_installed(self):
        user = create_test_user()
        app = create_test_app()
        result = get_user_installation(user=user, app=app)
        self.assertIsNone(result)


class GetReviewSelectorTests(TestCase):
    def test_get_review_returns_object(self):
        user = create_test_user()
        app = create_test_app()
        review = create_test_review(app=app, user=user, rating=5)
        result = get_review()
        self.assertEqual(review, result)

    def test_get_reviews_returns_queryset(self):
        user = create_test_user()
        app = create_test_app()
        create_test_review(app=app, user=user, rating=3)
        create_test_review(app=create_test_app(name="App 2"), user=user, rating=5)
        result = get_reviews()
        self.assertEqual(2, result.count())


class GetInstallationSelectorTests(TestCase):
    def test_get_installation_returns_object(self):
        user = create_test_user()
        app = create_test_app()
        installation = create_test_installation(app=app, user=user)
        result = get_installation()
        self.assertEqual(installation, result)

    def test_get_installations_returns_queryset(self):
        user = create_test_user()
        app1 = create_test_app(name="App 1")
        app2 = create_test_app(name="App 2")
        create_test_installation(app=app1, user=user)
        create_test_installation(app=app2, user=user)
        result = get_installations()
        self.assertEqual(2, result.count())
