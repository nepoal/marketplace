from django.contrib import admin

from open_schools_platform.marketplace_management.admin.mixins import (
    MarketplaceModelAdmin,
    _is_staff_or_superuser,
    _is_chief_moderator,
)
from open_schools_platform.marketplace_management.models import ModeratorProfile


@admin.register(ModeratorProfile)
class ModeratorProfileAdmin(MarketplaceModelAdmin):
    list_display = ("user", "is_chief", "created_at")
    list_filter = ("is_chief",)
    search_fields = ("user__name",)

    def has_view_permission(self, request, obj=None):
        if _is_staff_or_superuser(request.user):
            return True
        return _is_chief_moderator(request.user)

    def has_add_permission(self, request):
        if _is_staff_or_superuser(request.user):
            return True
        return _is_chief_moderator(request.user)

    def has_change_permission(self, request, obj=None):
        if _is_staff_or_superuser(request.user):
            return True
        return _is_chief_moderator(request.user)

    def has_delete_permission(self, request, obj=None):
        if _is_staff_or_superuser(request.user):
            return True
        return _is_chief_moderator(request.user)
