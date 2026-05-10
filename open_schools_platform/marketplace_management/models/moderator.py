import uuid

from django.db import models

from open_schools_platform.common.models import BaseModel, BaseManager
from open_schools_platform.user_management.users.models import User


class ModeratorProfileManager(BaseManager):
    def create_moderator(self, user, is_chief: bool = False):
        profile = self.model(user=user, is_chief=is_chief)
        profile.full_clean()
        profile.save(using=self._db)
        return profile


class ModeratorProfile(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="moderator_profile"
    )
    is_chief = models.BooleanField(default=False)

    objects = ModeratorProfileManager()

    def __str__(self):
        role = "Chief Moderator" if self.is_chief else "Moderator"
        return f"{role}: {self.user}"
