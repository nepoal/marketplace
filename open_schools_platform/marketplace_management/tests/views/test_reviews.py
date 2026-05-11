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
from open_schools_platform.user_management.users.tests.utils import create_logged_in_user, create_test_user

NS = "api:marketplace-management:marketplace"


class AppReviewListApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = lambda pk: reverse(f"{NS}:marketplace-apps-reviews", args=[pk])

    def test_returns_app_reviews(self):
        user = create_test_user()
        app = create_test_app()
        create_test_review(app=app, user=user, rating=5, message="Great!")
        response = self.client.get(self.url(app.id))
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, response.data["count"])

    def test_not_found_returns_404(self):
        response = self.client.get(self.url(uuid.uuid4()))
        self.assertEqual(404, response.status_code)

    def test_anonymous_access_allowed(self):
        app = create_test_app()
        response = self.client.get(self.url(app.id))
        self.assertEqual(200, response.status_code)

    def test_does_not_return_reviews_from_other_apps(self):
        user = create_test_user()
        app1 = create_test_app(name="App 1")
        app2 = create_test_app(name="App 2")
        create_test_review(app=app2, user=user, rating=4)
        response = self.client.get(self.url(app1.id))
        self.assertEqual(0, response.data["count"])

    def test_review_contains_user_name_and_rating(self):
        user = create_test_user()
        app = create_test_app()
        create_test_review(app=app, user=user, rating=4, message="Good")
        response = self.client.get(self.url(app.id))
        review = response.data["results"][0]
        self.assertIn("user_name", review)
        self.assertIn("rating", review)
        self.assertEqual(4, review["rating"])


class AppReviewCreateUpdateApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = lambda pk: reverse(f"{NS}:marketplace-apps-review", args=[pk])

    def test_create_review_success(self):
        user = create_logged_in_user(instance=self)
        app = create_test_app()
        create_test_installation(app=app, user=user)
        response = self.client.post(self.url(app.id), {"rating": 5, "message": "Excellent!"})
        self.assertEqual(200, response.status_code)
        self.assertIn("review", response.data)
        self.assertEqual(1, Review.objects.count())

    def test_update_existing_review(self):
        user = create_logged_in_user(instance=self)
        app = create_test_app()
        create_test_installation(app=app, user=user)
        self.client.post(self.url(app.id), {"rating": 3, "message": "OK"})
        response = self.client.post(self.url(app.id), {"rating": 5, "message": "Great!"})
        self.assertEqual(200, response.status_code)
        self.assertEqual(5, response.data["review"]["rating"])
        self.assertEqual(1, Review.objects.count())

    def test_create_without_installation_returns_400(self):
        create_logged_in_user(instance=self)
        app = create_test_app()
        response = self.client.post(self.url(app.id), {"rating": 5})
        self.assertEqual(400, response.status_code)

    def test_invalid_rating_returns_400(self):
        user = create_logged_in_user(instance=self)
        app = create_test_app()
        create_test_installation(app=app, user=user)
        response = self.client.post(self.url(app.id), {"rating": 6})
        self.assertEqual(400, response.status_code)

    def test_delete_review_success(self):
        user = create_logged_in_user(instance=self)
        app = create_test_app()
        create_test_installation(app=app, user=user)
        create_test_review(app=app, user=user, rating=4)
        response = self.client.delete(self.url(app.id))
        self.assertEqual(204, response.status_code)
        self.assertEqual(0, Review.objects.count())

    def test_delete_nonexistent_review_returns_404(self):
        create_logged_in_user(instance=self)
        app = create_test_app()
        response = self.client.delete(self.url(app.id))
        self.assertEqual(404, response.status_code)

    def test_unauthorized_post_returns_401(self):
        app = create_test_app()
        response = self.client.post(self.url(app.id), {"rating": 5})
        self.assertEqual(401, response.status_code)

    def test_unauthorized_delete_returns_401(self):
        app = create_test_app()
        response = self.client.delete(self.url(app.id))
        self.assertEqual(401, response.status_code)

    def test_app_not_found_returns_404(self):
        create_logged_in_user(instance=self)
        response = self.client.post(self.url(uuid.uuid4()), {"rating": 5})
        self.assertEqual(404, response.status_code)
