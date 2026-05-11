from django.test import TestCase
from rest_framework.exceptions import ValidationError

from open_schools_platform.marketplace_management.models import ModeratorProfile
from open_schools_platform.marketplace_management.services.moderator import (
    create_moderator,
    update_moderator,
)
from open_schools_platform.marketplace_management.tests.utils import create_test_moderator
from open_schools_platform.user_management.users.tests.utils import create_test_user


class CreateModeratorTests(TestCase):
    def test_creates_regular_moderator(self):
        user = create_test_user()
        profile = create_moderator(user=user)
        self.assertFalse(profile.is_chief)
        self.assertEqual(user, profile.user)

    def test_creates_chief_moderator(self):
        user = create_test_user()
        profile = create_moderator(user=user, is_chief=True)
        self.assertTrue(profile.is_chief)

    def test_duplicate_raises_validation_error(self):
        user = create_test_user()
        create_test_moderator(user=user)
        with self.assertRaises(ValidationError):
            create_moderator(user=user)


class UpdateModeratorTests(TestCase):
    def test_update_is_chief_to_false(self):
        user = create_test_user()
        profile = create_test_moderator(user=user, is_chief=True)
        updated = update_moderator(profile=profile, data={"is_chief": False})
        self.assertFalse(updated.is_chief)

    def test_update_is_chief_to_true(self):
        user = create_test_user()
        profile = create_test_moderator(user=user, is_chief=False)
        updated = update_moderator(profile=profile, data={"is_chief": True})
        self.assertTrue(updated.is_chief)
