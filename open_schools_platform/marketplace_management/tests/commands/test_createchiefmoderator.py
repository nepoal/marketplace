from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from open_schools_platform.marketplace_management.models import ModeratorProfile
from open_schools_platform.marketplace_management.tests.utils import (
    create_test_moderator,
)
from open_schools_platform.user_management.users.tests.utils import create_test_user


class CreateChiefModeratorCommandTests(TestCase):
    def _call(self, phone, demote=False):
        out = StringIO()
        args = ["createchiefmoderator", phone]
        if demote:
            args.append("--demote")
        call_command(*args, stdout=out)
        return out.getvalue()

    def test_user_not_found_raises_error(self):
        with self.assertRaises(CommandError):
            self._call("+70000000000")

    def test_promote_creates_new_profile(self):
        user = create_test_user()
        output = self._call(str(user.phone))
        self.assertIn("created and granted", output)
        profile = ModeratorProfile.objects.get(user=user)
        self.assertTrue(profile.is_chief)

    def test_promote_updates_existing_profile(self):
        user = create_test_user()
        create_test_moderator(user=user, is_chief=False)
        output = self._call(str(user.phone))
        self.assertIn("updated", output)
        self.assertTrue(ModeratorProfile.objects.get(user=user).is_chief)

    def test_demote_deletes_moderator_profile(self):
        user = create_test_user()
        create_test_moderator(user=user, is_chief=True)
        output = self._call(str(user.phone), demote=True)
        self.assertIn("removed", output)
        self.assertFalse(ModeratorProfile.objects.filter(user=user).exists())

    def test_demote_already_not_chief_prints_warning(self):
        user = create_test_user()
        create_test_moderator(user=user, is_chief=False)
        output = self._call(str(user.phone), demote=True)
        self.assertIn("Nothing changed", output)
        self.assertTrue(ModeratorProfile.objects.filter(user=user).exists())

    def test_demote_no_profile_prints_warning(self):
        user = create_test_user()
        output = self._call(str(user.phone), demote=True)
        self.assertIn("Nothing changed", output)
        self.assertFalse(ModeratorProfile.objects.filter(user=user).exists())
