from django.contrib import admin

from open_schools_platform.marketplace_management.models import ModeratorProfile


def _is_moderator(user) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    return ModeratorProfile.objects.filter(user=user).exists()


def _is_chief_moderator(user) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    return ModeratorProfile.objects.filter(user=user, is_chief=True).exists()


def _is_staff_or_superuser(user) -> bool:
    return getattr(user, "is_superuser", False) or getattr(user, "is_admin", False)


class _MarketplaceAwareAdminSite(admin.site.__class__):
    """Admin site that grants access to staff, superusers, and marketplace moderators.

    Moderators see only the marketplace_management section of the admin;
    staff and superusers see everything.
    """

    def has_permission(self, request):
        if not request.user.is_active:
            return False
        if _is_staff_or_superuser(request.user):
            return True
        return _is_moderator(request.user)

    def get_app_list(self, request):
        app_list = super().get_app_list(request)
        if _is_staff_or_superuser(request.user):
            return app_list
        if _is_moderator(request.user):
            return [a for a in app_list if a["app_label"] == "marketplace_management"]
        return []


admin.site.__class__ = _MarketplaceAwareAdminSite


class MarketplaceModelAdmin(admin.ModelAdmin):
    """Base ModelAdmin that allows access to staff/superusers and moderators.

    Delete permission is restricted to chief moderators and above.
    """

    def _user_can_access(self, request) -> bool:
        return _is_staff_or_superuser(request.user) or _is_moderator(request.user)

    def has_module_permission(self, request):
        return self._user_can_access(request)

    def has_view_permission(self, request, obj=None):
        return self._user_can_access(request)

    def has_add_permission(self, request):
        return self._user_can_access(request)

    def has_change_permission(self, request, obj=None):
        return self._user_can_access(request)

    def has_delete_permission(self, request, obj=None):
        if _is_staff_or_superuser(request.user):
            return True
        return _is_chief_moderator(request.user)


class MarketplaceInlineMixin:
    """Mixin for inline admins that applies the same permission rules as MarketplaceModelAdmin."""

    def _user_can_access(self, request):
        return _is_staff_or_superuser(request.user) or _is_moderator(request.user)

    def has_view_permission(self, request, obj=None):
        return self._user_can_access(request)

    def has_add_permission(self, request, obj=None):
        return self._user_can_access(request)

    def has_change_permission(self, request, obj=None):
        return self._user_can_access(request)

    def has_delete_permission(self, request, obj=None):
        if _is_staff_or_superuser(request.user):
            return True
        return _is_chief_moderator(request.user)
