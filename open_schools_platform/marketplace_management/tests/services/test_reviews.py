from django.test import TestCase
from rest_framework.exceptions import PermissionDenied, ValidationError

from open_schools_platform.marketplace_management.models import Review
from open_schools_platform.marketplace_management.services.app import (
    create_or_update_review,
    delete_review,
)
from open_schools_platform.marketplace_management.tests.utils import (
    create_test_app,
    create_test_installation,
)
from open_schools_platform.user_management.users.tests.utils import create_test_user


class CreateOrUpdateReviewTests(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.app = create_test_app()
        create_test_installation(app=self.app, user=self.user)

    def test_create_new_review(self):
        review = create_or_update_review(
            app=self.app, user=self.user, rating=4, message="Great!"
        )
        self.assertEqual(4, review.rating)
        self.assertEqual("Great!", review.message)
        self.assertEqual(1, Review.objects.count())

    def test_update_existing_review(self):
        create_or_update_review(app=self.app, user=self.user, rating=3, message="OK")
        review = create_or_update_review(
            app=self.app, user=self.user, rating=5, message="Excellent!"
        )
        self.assertEqual(5, review.rating)
        self.assertEqual("Excellent!", review.message)
        self.assertEqual(1, Review.objects.count())

    def test_create_without_installation_raises_error(self):
        other_user = create_test_user(phone="+79999999999")
        with self.assertRaises(ValidationError):
            create_or_update_review(app=self.app, user=other_user, rating=3)

    def test_review_rating_boundaries(self):
        review = create_or_update_review(app=self.app, user=self.user, rating=1)
        self.assertEqual(1, review.rating)
        review = create_or_update_review(app=self.app, user=self.user, rating=5)
        self.assertEqual(5, review.rating)

    def test_review_with_empty_message(self):
        review = create_or_update_review(
            app=self.app, user=self.user, rating=3, message=""
        )
        self.assertEqual("", review.message)


class DeleteReviewTests(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.app = create_test_app()
        create_test_installation(app=self.app, user=self.user)
        self.review = create_or_update_review(app=self.app, user=self.user, rating=5)

    def test_successful_deletion(self):
        delete_review(review=self.review, user=self.user)
        self.assertEqual(0, Review.objects.count())

    def test_delete_other_users_review_raises_permission_denied(self):
        other_user = create_test_user(phone="+79999999999")
        with self.assertRaises(PermissionDenied):
            delete_review(review=self.review, user=other_user)
