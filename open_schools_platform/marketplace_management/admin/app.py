from django.contrib import admin

from open_schools_platform.marketplace_management.admin.mixins import (
    MarketplaceModelAdmin,
    MarketplaceInlineMixin,
)
from open_schools_platform.marketplace_management.models import (
    App,
    AppVersion,
    AppUrl,
    Category,
    OidcClient,
)


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
