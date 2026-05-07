from rest_framework import serializers

from open_schools_platform.marketplace_management.models import (
    App,
    AppVersion,
    AppUrl,
    Category,
    Installation,
    Review,
    Payment,
)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name")


class AppUrlSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppUrl
        fields = ("base_url", "launch_path", "launch_url")


class AppVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppVersion
        fields = ("id", "version", "description", "date")


class AppListSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    average_rating = serializers.FloatField(read_only=True)
    reviews_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = App
        fields = (
            "id",
            "name",
            "short_description",
            "status",
            "icon_url",
            "category",
            "is_free",
            "amount",
            "currency",
            "average_rating",
            "reviews_count",
            "created_at",
        )


class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.name", read_only=True)

    class Meta:
        model = Review
        fields = ("id", "user_name", "rating", "message", "created_at", "updated_at")


class AppDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    latest_version = serializers.SerializerMethodField()
    reviews = ReviewSerializer(many=True, read_only=True)
    average_rating = serializers.FloatField(read_only=True)
    reviews_count = serializers.IntegerField(read_only=True)

    def get_latest_version(self, obj):
        version = obj.versions.order_by("-date").first()
        return AppVersionSerializer(version).data if version else None

    class Meta:
        model = App
        fields = (
            "id",
            "name",
            "short_description",
            "description",
            "status",
            "icon_url",
            "screenshots",
            "category",
            "latest_version",
            "is_free",
            "amount",
            "currency",
            "average_rating",
            "reviews_count",
            "reviews",
            "created_at",
            "updated_at",
        )


class CreateReviewSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    message = serializers.CharField(max_length=2000, allow_blank=True, default="")


class UpdateReviewSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5, required=False)
    message = serializers.CharField(max_length=2000, allow_blank=True, required=False)


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ("id", "amount", "currency", "status", "created_at")


class InstallationSerializer(serializers.ModelSerializer):
    app = AppListSerializer(read_only=True)
    payment = PaymentSerializer(read_only=True)

    class Meta:
        model = Installation
        fields = ("id", "app", "active", "payment", "created_at", "expires_at")


class AppLaunchResponseSerializer(serializers.Serializer):
    launch_url = serializers.URLField()
    launch_token = serializers.CharField()
    expires_at = serializers.DateTimeField()


class OidcTokenResponseSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    token_type = serializers.CharField()
    expires_in = serializers.IntegerField()
    refresh_token = serializers.CharField()
    id_token = serializers.CharField()
    scope = serializers.CharField()


class OidcUserInfoSerializer(serializers.Serializer):
    sub = serializers.CharField()
    name = serializers.CharField()
    phone = serializers.CharField()
