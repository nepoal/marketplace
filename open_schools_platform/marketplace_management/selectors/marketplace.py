from django.db.models import QuerySet

from open_schools_platform.common.selectors import selector_factory
from open_schools_platform.marketplace_management.filters import (
    ReviewFilter,
    InstallationFilter,
)
from open_schools_platform.marketplace_management.models import (
    App,
    Review,
    Installation,
)
from open_schools_platform.user_management.users.models import User


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


def get_user_review(user: User, app: App) -> Review:
    return Review.objects.filter(user=user, app=app).first()


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


def get_user_installation(user: User, app: App) -> Installation:
    return Installation.objects.filter(user=user, app=app).first()
