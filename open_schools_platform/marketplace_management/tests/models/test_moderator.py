from django.test import TestCase

from open_schools_platform.marketplace_management.models import ModeratorProfile
from open_schools_platform.user_management.users.tests.utils import create_test_user


class ModeratorProfileStrTests(TestCase):
    def test_chief_str(self):
        user = create_test_user()
        profile = ModeratorProfile.objects.create_moderator(user=user, is_chief=True)
        self.assertIn("Chief Moderator", str(profile))

    def test_regular_str(self):
        user = create_test_user()
        profile = ModeratorProfile.objects.create_moderator(user=user, is_chief=False)
        self.assertIn("Moderator", str(profile))
        self.assertNotIn("Chief", str(profile))


class ModeratorProfileManagerTests(TestCase):
    def test_create_moderator_saves_to_db(self):
        user = create_test_user()
        profile = ModeratorProfile.objects.create_moderator(user=user)
        self.assertEqual(1, ModeratorProfile.objects.count())
        self.assertEqual(user, profile.user)
        self.assertFalse(profile.is_chief)

    def test_create_moderator_with_is_chief(self):
        user = create_test_user()
        profile = ModeratorProfile.objects.create_moderator(user=user, is_chief=True)
        self.assertTrue(profile.is_chief)
