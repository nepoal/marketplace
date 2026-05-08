from django_filters import CharFilter, OrderingFilter, BooleanFilter, UUIDFilter

from open_schools_platform.common.filters import BaseFilterSet
from open_schools_platform.marketplace_management.models import (
    App,
    Review,
    Installation,
)


class AppFilter(BaseFilterSet):
    name = CharFilter(field_name="name", lookup_expr="icontains")
    short_description = CharFilter(
        field_name="short_description", lookup_expr="icontains"
    )
    status = CharFilter(field_name="status", lookup_expr="exact")
    category = UUIDFilter(field_name="categories__id")
    category_name = CharFilter(field_name="categories__name", lookup_expr="icontains")
    is_free = BooleanFilter(field_name="is_free")
    or_search = CharFilter(field_name="or_search", method="OR")

    order = OrderingFilter(
        fields=(
            ("name", "name"),
            ("created_at", "created_at"),
            ("amount", "price"),
        )
    )

    class Meta:
        model = App
        fields = ("id", "status", "is_free")


class ReviewFilter(BaseFilterSet):
    app = UUIDFilter(field_name="app__id")
    user = UUIDFilter(field_name="user__id")

    class Meta:
        model = Review
        fields = ("id", "rating")


class InstallationFilter(BaseFilterSet):
    app = UUIDFilter(field_name="app__id")
    user = UUIDFilter(field_name="user__id")
    active = BooleanFilter(field_name="active")

    class Meta:
        model = Installation
        fields = ("id", "active")
