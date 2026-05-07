from django.db.models import QuerySet

from open_schools_platform.common.selectors import selector_factory
from open_schools_platform.marketplace_management.filters import (
    AppFilter,
    ReviewFilter,
    InstallationFilter,
)
from open_schools_platform.marketplace_management.models import (
    App,
    Review,
    Installation,
    OidcClient,
    OidcAuthorizationCode,
    OidcAccessToken,
    OidcRefreshToken,
    AppLaunch,
    Category,
)
from open_schools_platform.user_management.users.models import User


@selector_factory(App)
def get_apps(*, filters=None, prefetch_related_list=None) -> QuerySet:
    filters = filters or {}
    qs = (
        App.objects.prefetch_related(*prefetch_related_list)
        .select_related("category")
        .all()
    )
    return AppFilter(filters, qs).qs


@selector_factory(App)
def get_app(*, filters=None, prefetch_related_list=None) -> App:
    filters = filters or {}
    qs = (
        App.objects.prefetch_related(*prefetch_related_list, "reviews__user")
        .select_related("category")
        .all()
    )
    return AppFilter(filters, qs).qs.first()


@selector_factory(Review)
def get_reviews(*, filters=None, prefetch_related_list=None) -> QuerySet:
    filters = filters or {}
    qs = (
        Review.objects.prefetch_related(*prefetch_related_list)
        .select_related("user")
        .all()
    )
    return ReviewFilter(filters, qs).qs


@selector_factory(Review)
def get_review(*, filters=None, prefetch_related_list=None) -> Review:
    filters = filters or {}
    qs = Review.objects.select_related("user").all()
    return ReviewFilter(filters, qs).qs.first()


@selector_factory(Installation)
def get_installations(*, filters=None, prefetch_related_list=None) -> QuerySet:
    filters = filters or {}
    qs = (
        Installation.objects.prefetch_related(*prefetch_related_list)
        .select_related("app", "user")
        .all()
    )
    return InstallationFilter(filters, qs).qs


@selector_factory(Installation)
def get_installation(*, filters=None, prefetch_related_list=None) -> Installation:
    filters = filters or {}
    qs = Installation.objects.select_related("app", "user").all()
    return InstallationFilter(filters, qs).qs.first()


@selector_factory(OidcClient)
def get_oidc_client(*, filters=None, prefetch_related_list=None) -> OidcClient:
    filters = filters or {}
    qs = OidcClient.objects.select_related("app").all()
    if "client_id" in filters:
        qs = qs.filter(client_id=filters["client_id"])
    if "id" in filters:
        qs = qs.filter(id=filters["id"])
    return qs.first()


@selector_factory(OidcAuthorizationCode)
def get_auth_code(*, filters=None, prefetch_related_list=None) -> OidcAuthorizationCode:
    filters = filters or {}
    qs = OidcAuthorizationCode.objects.select_related("client", "user").all()
    if "code" in filters:
        qs = qs.filter(code=filters["code"])
    return qs.first()


@selector_factory(OidcAccessToken)
def get_access_token(*, filters=None, prefetch_related_list=None) -> OidcAccessToken:
    filters = filters or {}
    qs = OidcAccessToken.objects.select_related("client", "user").all()
    if "token" in filters:
        qs = qs.filter(token=filters["token"])
    return qs.first()


@selector_factory(OidcRefreshToken)
def get_refresh_token(*, filters=None, prefetch_related_list=None) -> OidcRefreshToken:
    filters = filters or {}
    qs = OidcRefreshToken.objects.select_related("client", "user").all()
    if "token" in filters:
        qs = qs.filter(token=filters["token"])
    return qs.first()


@selector_factory(AppLaunch)
def get_app_launch(*, filters=None, prefetch_related_list=None) -> AppLaunch:
    filters = filters or {}
    qs = AppLaunch.objects.select_related("app", "user").all()
    if "launch_token" in filters:
        qs = qs.filter(launch_token=filters["launch_token"])
    if "id" in filters:
        qs = qs.filter(id=filters["id"])
    return qs.first()


@selector_factory(Category)
def get_categories(*, filters=None, prefetch_related_list=None) -> QuerySet:
    filters = filters or {}
    return Category.objects.all()


@selector_factory(Category)
def get_category(*, filters=None, prefetch_related_list=None) -> Category:
    filters = filters or {}
    qs = Category.objects.all()
    if "id" in filters:
        qs = qs.filter(id=filters["id"])
    if "name" in filters:
        qs = qs.filter(name=filters["name"])
    return qs.first()


def get_user_installation(user: User, app: App) -> Installation:
    return Installation.objects.filter(user=user, app=app).first()


def get_user_review(user: User, app: App) -> Review:
    return Review.objects.filter(user=user, app=app).first()
