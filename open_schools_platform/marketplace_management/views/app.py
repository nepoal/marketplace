from drf_yasg.utils import swagger_auto_schema
from rest_framework.exceptions import NotFound
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from open_schools_platform.api.mixins import ApiAuthMixin
from open_schools_platform.api.pagination import get_paginated_response
from open_schools_platform.api.swagger_tags import SwaggerTags
from open_schools_platform.common.views import convert_dict_to_serializer
from open_schools_platform.marketplace_management.filters import (
    AppFilter,
    ReviewFilter,
    InstallationFilter,
)
from open_schools_platform.marketplace_management.models import (
    App,
    Installation,
    Review,
)
from open_schools_platform.marketplace_management.paginators import (
    AppListPagination,
    ReviewListPagination,
    InstallationListPagination,
)
from open_schools_platform.marketplace_management.selectors import (
    get_app,
    get_apps,
    get_reviews,
    get_installations,
    get_user_review,
    get_categories,
)
from open_schools_platform.marketplace_management.serializers import (
    AppListSerializer,
    AppDetailSerializer,
    ReviewSerializer,
    CreateUpdateReviewSerializer,
    InstallationSerializer,
    PaymentSerializer,
    AppLaunchResponseSerializer,
    CategorySerializer,
)
from open_schools_platform.marketplace_management.services import (
    create_or_update_review,
    delete_review,
    install_app,
    uninstall_app,
    create_app_launch,
    build_launch_url,
    create_payment,
)

TAGS = [SwaggerTags.MARKETPLACE_MANAGEMENT]


class CategoryListApi(ApiAuthMixin, APIView):

    @swagger_auto_schema(
        operation_description="Get all app categories",
        tags=TAGS,
        responses={
            200: convert_dict_to_serializer(
                {"categories": CategorySerializer(many=True)}
            )
        },
    )
    def get(self, request):
        categories = get_categories(filters={})
        return Response({"categories": CategorySerializer(categories, many=True).data})


class AppListApi(ApiAuthMixin, ListAPIView):
    queryset = App.objects.all()
    filterset_class = AppFilter
    pagination_class = AppListPagination
    serializer_class = AppListSerializer

    @swagger_auto_schema(
        operation_description=(
            "List marketplace apps. Supports filtering by name, "
            "category, status, is_free and sorting."
        ),
        tags=TAGS,
    )
    def get(self, request, *args, **kwargs):
        return get_paginated_response(
            pagination_class=AppListPagination,
            serializer_class=AppListSerializer,
            queryset=get_apps(filters=request.GET.dict()),
            request=request,
            view=self,
        )


class AppDetailApi(ApiAuthMixin, APIView):

    @swagger_auto_schema(
        operation_description="Get detailed information about an app.",
        tags=TAGS,
        responses={
            200: convert_dict_to_serializer({"app": AppDetailSerializer()}),
            404: "Not found",
        },
    )
    def get(self, request, app_id):
        app = get_app(filters={"id": str(app_id)}, empty_exception=True)
        return Response({"app": AppDetailSerializer(app).data})


class AppInstallApi(ApiAuthMixin, APIView):
    @swagger_auto_schema(
        operation_description="Install an app for the current user.",
        tags=TAGS,
        responses={
            201: convert_dict_to_serializer({"installation": InstallationSerializer()}),
            404: "Not found",
        },
    )
    def post(self, request, app_id):
        app = get_app(filters={"id": str(app_id)}, empty_exception=True)
        installation = install_app(app=app, user=request.user)
        return Response(
            {"installation": InstallationSerializer(installation).data}, status=201
        )


class AppUninstallApi(ApiAuthMixin, APIView):
    @swagger_auto_schema(
        operation_description="Uninstall an app for the current user.",
        tags=TAGS,
        responses={204: "Successfully uninstalled", 404: "Not found"},
    )
    def delete(self, request, app_id):
        app = get_app(filters={"id": str(app_id)}, empty_exception=True)
        uninstall_app(app=app, user=request.user)
        return Response(status=204)


class AppPayApi(ApiAuthMixin, APIView):
    @swagger_auto_schema(
        operation_description=(
            "Pay for a paid app. Price is taken from the app record at the time of payment."
        ),
        tags=TAGS,
        responses={
            201: PaymentSerializer(),
            400: "App is free or payment already exists",
            404: "Not found",
        },
    )
    def post(self, request, app_id):
        app = get_app(filters={"id": str(app_id)}, empty_exception=True)
        payment = create_payment(app=app, user=request.user)
        return Response(PaymentSerializer(payment).data, status=201)


class AppLaunchApi(ApiAuthMixin, APIView):
    @swagger_auto_schema(
        operation_description=(
            "Get a launch URL for opening an installed app in an iframe."
            "The returned launch_token is single-use and expires in 5 minutes."
        ),
        tags=TAGS,
        responses={200: AppLaunchResponseSerializer()},
    )
    def get(self, request, app_id):
        app = get_app(filters={"id": str(app_id)}, empty_exception=True)
        launch = create_app_launch(app=app, user=request.user)
        launch_url = build_launch_url(app_launch=launch)
        return Response(
            {
                "launch_url": launch_url,
                "launch_token": launch.launch_token,
                "expires_at": launch.token_exp,
            }
        )


class UserInstallationListApi(ApiAuthMixin, ListAPIView):
    queryset = Installation.objects.all()
    filterset_class = InstallationFilter
    pagination_class = InstallationListPagination
    serializer_class = InstallationSerializer

    @swagger_auto_schema(
        operation_description="List all apps installed by the current user.",
        tags=TAGS,
    )
    def get(self, request, *args, **kwargs):
        filters = request.GET.dict()
        filters["user"] = str(request.user.id)
        return get_paginated_response(
            pagination_class=InstallationListPagination,
            serializer_class=InstallationSerializer,
            queryset=get_installations(filters=filters),
            request=request,
            view=self,
        )


class AppReviewListApi(ApiAuthMixin, ListAPIView):
    queryset = Review.objects.all()
    filterset_class = ReviewFilter
    pagination_class = ReviewListPagination
    serializer_class = ReviewSerializer

    @swagger_auto_schema(
        operation_description="List reviews for an app.",
        tags=TAGS,
    )
    def get(self, request, app_id):
        get_app(filters={"id": str(app_id)}, empty_exception=True)
        return get_paginated_response(
            pagination_class=ReviewListPagination,
            serializer_class=ReviewSerializer,
            queryset=get_reviews(filters={"app": str(app_id)}),
            request=request,
            view=self,
        )


class AppReviewCreateUpdateApi(ApiAuthMixin, APIView):
    @swagger_auto_schema(
        operation_description="Create or update a review for an installed app.",
        request_body=CreateUpdateReviewSerializer,
        tags=TAGS,
        responses={200: convert_dict_to_serializer({"review": ReviewSerializer()})},
    )
    def post(self, request, app_id):
        app = get_app(filters={"id": str(app_id)}, empty_exception=True)
        serializer = CreateUpdateReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = create_or_update_review(
            app=app,
            user=request.user,
            **serializer.validated_data,
        )
        return Response({"review": ReviewSerializer(review).data}, status=200)

    @swagger_auto_schema(
        operation_description="Delete the current user's review for an app.",
        tags=TAGS,
        responses={204: "Deleted", 404: "Not found"},
    )
    def delete(self, request, app_id):
        app = get_app(filters={"id": str(app_id)}, empty_exception=True)
        review = get_user_review(user=request.user, app=app)
        if not review:
            raise NotFound("You have not reviewed this app.")
        delete_review(review=review, user=request.user)
        return Response(status=204)
