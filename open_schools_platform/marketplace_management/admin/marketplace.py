from django.contrib import admin

from open_schools_platform.marketplace_management.admin.mixins import MarketplaceModelAdmin
from open_schools_platform.marketplace_management.models import (
    Review,
    Installation,
    Payment,
)


@admin.register(Review)
class ReviewAdmin(MarketplaceModelAdmin):
    list_display = ("app", "user", "rating", "created_at")
    list_filter = ("rating", "app")
    search_fields = ("app__name", "user__name")
    readonly_fields = ("app", "user", "rating", "message", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Installation)
class InstallationAdmin(MarketplaceModelAdmin):
    list_display = ("app", "user", "active", "created_at", "expires_at")
    list_filter = ("active", "app")
    search_fields = ("app__name", "user__name")
    readonly_fields = ("app", "user", "created_at")

    def has_add_permission(self, request):
        return False


@admin.register(Payment)
class PaymentAdmin(MarketplaceModelAdmin):
    list_display = ("app", "user", "amount", "currency", "status", "created_at")
    list_filter = ("status", "currency", "app")
    search_fields = ("app__name", "user__name")
    readonly_fields = ("app", "user", "amount", "currency", "created_at")

    def has_add_permission(self, request):
        return False
