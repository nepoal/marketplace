from rest_framework.exceptions import ValidationError

from open_schools_platform.common.services import model_update
from open_schools_platform.marketplace_management.models import ModeratorProfile
from open_schools_platform.user_management.users.models import User


def create_moderator(*, user: User, is_chief: bool = False) -> ModeratorProfile:
    if hasattr(user, "moderator_profile"):
        raise ValidationError("This user is already a moderator.")
    return ModeratorProfile.objects.create_moderator(user=user, is_chief=is_chief)


def update_moderator(*, profile: ModeratorProfile, data: dict) -> ModeratorProfile:
    profile, _ = model_update(instance=profile, fields=["is_chief"], data=data)
    return profile
