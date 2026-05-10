from django.db.models import QuerySet

from open_schools_platform.common.selectors import selector_factory
from open_schools_platform.marketplace_management.filters import AppFilter
from open_schools_platform.marketplace_management.models import App, AppLaunch, Category


@selector_factory(App)
def get_apps(*, filters=None, prefetch_related_list=None) -> QuerySet:
    filters = filters or {}
    qs = App.objects.prefetch_related(*prefetch_related_list, "categories").all()
    return AppFilter(filters, qs).qs.distinct()


@selector_factory(App)
def get_app(*, filters=None, prefetch_related_list=None) -> App:
    filters = filters or {}
    qs = App.objects.prefetch_related(
        *prefetch_related_list, "categories", "reviews__user"
    ).all()
    return AppFilter(filters, qs).qs.first()


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
