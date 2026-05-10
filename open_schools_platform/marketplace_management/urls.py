from django.urls import path

from open_schools_platform.marketplace_management.views.app import (
    CategoryListApi,
    AppListApi,
    AppDetailApi,
    AppInstallApi,
    AppUninstallApi,
    AppPayApi,
    AppLaunchApi,
    UserInstallationListApi,
    AppReviewListApi,
    AppReviewCreateUpdateApi,
)
from open_schools_platform.marketplace_management.views.oidc import (
    OidcAuthApi,
    OidcTokenApi,
    OidcUserInfoApi,
)

urlpatterns = [
    # Categories
    path("categories", CategoryListApi.as_view(), name="marketplace-categories"),
    # App catalog
    path("apps", AppListApi.as_view(), name="marketplace-apps-list"),
    path("apps/<uuid:app_id>", AppDetailApi.as_view(), name="marketplace-apps-detail"),
    # Installations
    path(
        "apps/<uuid:app_id>/install",
        AppInstallApi.as_view(),
        name="marketplace-apps-install",
    ),
    path(
        "apps/<uuid:app_id>/uninstall",
        AppUninstallApi.as_view(),
        name="marketplace-apps-uninstall",
    ),
    path(
        "apps/<uuid:app_id>/pay",
        AppPayApi.as_view(),
        name="marketplace-apps-pay",
    ),
    path(
        "apps/<uuid:app_id>/launch",
        AppLaunchApi.as_view(),
        name="marketplace-apps-launch",
    ),
    path(
        "my/installations",
        UserInstallationListApi.as_view(),
        name="marketplace-my-installations",
    ),
    # Reviews
    path(
        "apps/<uuid:app_id>/reviews",
        AppReviewListApi.as_view(),
        name="marketplace-apps-reviews",
    ),
    path(
        "apps/<uuid:app_id>/review",
        AppReviewCreateUpdateApi.as_view(),
        name="marketplace-apps-review",
    ),
    # OIDC Provider
    path("oidc/auth", OidcAuthApi.as_view(), name="marketplace-oidc-auth"),
    path("oidc/token", OidcTokenApi.as_view(), name="marketplace-oidc-token"),
    path("oidc/userinfo", OidcUserInfoApi.as_view(), name="marketplace-oidc-userinfo"),
]
