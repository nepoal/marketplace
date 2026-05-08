from django.contrib import admin

from open_schools_platform.marketplace_management.models import (
    App,
    AppVersion,
    AppUrl,
    Category,
    Installation,
    Review,
    Payment,
    OidcClient,
    ModeratorProfile,
)


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


class AppVersionInline(MarketplaceInlineMixin, admin.TabularInline):
    model = AppVersion
    extra = 0
    readonly_fields = ("created_at",)


class AppUrlInline(MarketplaceInlineMixin, admin.StackedInline):
    model = AppUrl
    extra = 0
    readonly_fields = ("created_at",)


class OidcClientInline(MarketplaceInlineMixin, admin.StackedInline):
    model = OidcClient
    extra = 0
    readonly_fields = ("client_id", "created_at")
    exclude = ("client_secret_hash",)

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Category)
class CategoryAdmin(MarketplaceModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)


@admin.register(App)
class AppAdmin(MarketplaceModelAdmin):
    list_display = (
        "name",
        "status",
        "categories_display",
        "is_free",
        "average_rating_display",
        "created_at",
    )
    list_filter = ("status", "is_free", "categories")
    search_fields = ("name", "short_description")
    readonly_fields = (
        "created_at",
        "updated_at",
        "average_rating_display",
        "reviews_count_display",
    )
    inlines = [AppVersionInline, AppUrlInline, OidcClientInline]

    fieldsets = (
        (
            "General",
            {
                "fields": (
                    "name",
                    "short_description",
                    "description",
                    "categories",
                    "status",
                )
            },
        ),
        ("Media", {"fields": ("icon_url", "screenshots")}),
        ("Pricing", {"fields": ("is_free", "amount", "currency")}),
        (
            "Stats",
            {
                "fields": (
                    "average_rating_display",
                    "reviews_count_display",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    def categories_display(self, obj):
        return ", ".join(obj.categories.values_list("name", flat=True))

    categories_display.short_description = "Categories"

    def average_rating_display(self, obj):
        rating = obj.average_rating
        return f"{rating:.2f}" if rating is not None else "—"

    average_rating_display.short_description = "Average rating"

    def reviews_count_display(self, obj):
        return obj.reviews_count

    reviews_count_display.short_description = "Reviews count"

    def generate_oidc_credentials(self, request, queryset):
        from django.utils.html import format_html
        from open_schools_platform.marketplace_management.services import (
            create_oidc_client_for_app,
        )

        for app in queryset:
            if hasattr(app, "oidc_client"):
                self.message_user(
                    request,
                    f"{app.name} already has OIDC credentials.",
                    level="warning",
                )
                continue
            _, secret = create_oidc_client_for_app(app=app, redirect_uris=[])
            self.message_user(
                request,
                format_html(
                    "OIDC credentials created for <b>{}</b>. "
                    "Client ID: <code>{}</code>. "
                    "Secret (shown only once): <code>{}</code>",
                    app.name,
                    app.oidc_client.client_id,
                    secret,
                ),
            )

    generate_oidc_credentials.short_description = (
        "Generate OIDC credentials for selected apps"
    )
    actions = ["generate_oidc_credentials"]


@admin.register(AppVersion)
class AppVersionAdmin(MarketplaceModelAdmin):
    list_display = ("app", "version", "date", "created_at")
    list_filter = ("app",)
    search_fields = ("app__name", "version")


@admin.register(AppUrl)
class AppUrlAdmin(MarketplaceModelAdmin):
    list_display = ("app", "base_url", "launch_path")
    search_fields = ("app__name", "base_url")


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
