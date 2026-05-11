from django.core.management.base import BaseCommand, CommandError

from open_schools_platform.user_management.users.models import User
from open_schools_platform.marketplace_management.models import ModeratorProfile


class Command(BaseCommand):
    help = (
        "Grant chief moderator status to a user by phone number.\n"
        "Usage: python manage.py createchiefmoderator +79123456789\n"
        "Use --demote to remove chief moderator status."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "phone",
            type=str,
            help="Phone number of the user (e.g. +79123456789)",
        )
        parser.add_argument(
            "--demote",
            action="store_true",
            help="Remove chief moderator status instead of granting it",
        )

    def handle(self, *args, **options):
        phone = options["phone"]
        demote = options["demote"]

        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            raise CommandError(f"User with phone '{phone}' not found.")

        profile, created = ModeratorProfile.objects.get_or_create(user=user)

        if demote:
            if not profile.is_chief:
                self.stdout.write(
                    self.style.WARNING(
                        f"User {user} is not a chief moderator. Nothing changed."
                    )
                )
                return
            profile.is_chief = False
            profile.save(update_fields=["is_chief"])
            self.stdout.write(
                self.style.SUCCESS(
                    f"Chief moderator status removed from {user} ({phone})."
                )
            )
        else:
            profile.is_chief = True
            profile.save(update_fields=["is_chief"])
            action = "created and granted" if created else "updated — granted"
            self.stdout.write(
                self.style.SUCCESS(
                    f"Moderator profile {action} chief moderator status for {user} ({phone})."
                )
            )
