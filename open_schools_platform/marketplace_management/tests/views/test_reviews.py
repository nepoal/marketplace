import uuid

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from open_schools_platform.marketplace_management.models import Review
from open_schools_platform.marketplace_management.tests.utils import (
    create_test_app,
    create_test_installation,
    create_test_review,
)
from open_schools_platform.user_management.users.tests.utils import (
    create_logged_in_user,
    create_test_user,
)

NS = "api:marketplace-management:marketplace"


class AppReviewListApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = lambda pk: reverse(f"{NS}:marketplace-apps-reviews", args=[pk])

    def test_returns_app_reviews(self):
        create_logged_in_user(instance=self)
        user = create_test_user(phone="+79025456482")
        app = create_test_app()
        create_test_review(app=app, user=user, rating=5, message="Great!")
        response = self.client.get(self.url(app.id))
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, response.data["count"])

    def test_not_found_returns_404(self):
        create_logged_in_user(instance=self)
        response = self.client.get(self.url(uuid.uuid4()))
        self.assertEqual(404, response.status_code)

    def test_unauthorized_returns_401(self):
        app = create_test_app()
        response = self.client.get(self.url(app.id))
        self.assertEqual(401, response.status_code)

    def test_does_not_return_reviews_from_other_apps(self):
        create_logged_in_user(instance=self)
        user = create_test_user(phone="+79025456482")
        app1 = create_test_app(name="App 1")
        app2 = create_test_app(name="App 2")
        create_test_review(app=app2, user=user, rating=4)
        response = self.client.get(self.url(app1.id))
        self.assertEqual(0, response.data["count"])

    def test_review_contains_user_name_and_rating(self):
        create_logged_in_user(instance=self)
        user = create_test_user(phone="+79025456482")
        app = create_test_app()
        create_test_review(app=app, user=user, rating=4, message="Good")
        response = self.client.get(self.url(app.id))
        review = response.data["results"][0]
        self.assertIn("user_name", review)
        self.assertIn("rating", review)
        self.assertEqual(4, review["rating"])
