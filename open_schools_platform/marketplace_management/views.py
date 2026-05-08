from django.http import HttpResponse
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
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
    get_access_token,
    get_user_review,
    get_categories,
)
from open_schools_platform.marketplace_management.serializers import (
    AppListSerializer,
    AppDetailSerializer,
    ReviewSerializer,
    CreateReviewSerializer,
    InstallationSerializer,
    PaymentSerializer,
    AppLaunchResponseSerializer,
    OidcTokenResponseSerializer,
    OidcUserInfoSerializer,
    CategorySerializer,
)
from open_schools_platform.marketplace_management.oidc_server import (
    authorization_server,
)
from open_schools_platform.marketplace_management.services import (
    create_or_update_review,
    delete_review,
    install_app,
    uninstall_app,
    create_app_launch,
    build_launch_url,
    initiate_oidc_auth,
    create_payment,
)

TAGS = [SwaggerTags.MARKETPLACE_MANAGEMENT]


class CategoryListApi(APIView):
    permission_classes = (AllowAny,)

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


class AppListApi(ListAPIView):
    permission_classes = (AllowAny,)
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


class AppDetailApi(APIView):
    permission_classes = (AllowAny,)

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


class AppReviewListApi(ListAPIView):
    permission_classes = (AllowAny,)
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
        request_body=CreateReviewSerializer,
        tags=TAGS,
        responses={200: convert_dict_to_serializer({"review": ReviewSerializer()})},
    )
    def post(self, request, app_id):
        app = get_app(filters={"id": str(app_id)}, empty_exception=True)
        serializer = CreateReviewSerializer(data=request.data)
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


class OidcAuthApi(APIView):
    permission_classes = (AllowAny,)

    @swagger_auto_schema(
        operation_description=("OIDC Authorization endpoint."),
        tags=TAGS,
        manual_parameters=[
            openapi.Parameter(
                "client_id", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=True
            ),
            openapi.Parameter(
                "scope", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=True
            ),
            openapi.Parameter(
                "response_type",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                "redirect_uri",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                "nonce", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                "launch_token",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ],
        responses={302: "Redirect to redirect_uri with authorization code"},
    )
    def get(self, request):
        params = request.GET
        required = (
            "client_id",
            "scope",
            "response_type",
            "redirect_uri",
            "launch_token",
        )
        missing = [p for p in required if not params.get(p)]
        if missing:
            raise ValidationError(f"Missing required parameters: {', '.join(missing)}")

        redirect_url, _code, _id_token = initiate_oidc_auth(
            client_id=params["client_id"],
            redirect_uri=params["redirect_uri"],
            scope=params["scope"],
            response_type=params["response_type"],
            nonce=params.get("nonce", ""),
            launch_token=params["launch_token"],
        )
        return HttpResponse(status=302, headers={"Location": redirect_url})


class OidcTokenApi(APIView):
    permission_classes = (AllowAny,)

    @swagger_auto_schema(
        operation_description=("OIDC Token endpoint."),
        tags=TAGS,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "grant_type": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="authorization_code | refresh_token",
                ),
                "code": openapi.Schema(type=openapi.TYPE_STRING),
                "redirect_uri": openapi.Schema(type=openapi.TYPE_STRING),
                "client_id": openapi.Schema(type=openapi.TYPE_STRING),
                "client_secret": openapi.Schema(type=openapi.TYPE_STRING),
                "refresh_token": openapi.Schema(type=openapi.TYPE_STRING),
            },
            required=["grant_type"],
        ),
        responses={200: OidcTokenResponseSerializer()},
    )
    def post(self, request):
        import json

        http_response = authorization_server.create_token_response(request._request)
        try:
            data = json.loads(http_response.content)
        except (TypeError, ValueError):
            data = {"error": http_response.content.decode("utf-8", errors="replace")}
        return Response(data, status=http_response.status_code)


class OidcUserInfoApi(APIView):
    permission_classes = (AllowAny,)

    @swagger_auto_schema(
        operation_description=(
            "OIDC UserInfo endpoint."
            "Pass 'Authorization: Bearer <access_token>' header obtained from /oidc/token."
        ),
        tags=TAGS,
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER,
                type=openapi.TYPE_STRING,
                description="Bearer <access_token>",
                required=True,
            ),
        ],
        responses={200: OidcUserInfoSerializer(), 401: "Invalid or expired token"},
    )
    def get(self, request):
        from rest_framework.exceptions import AuthenticationFailed

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise AuthenticationFailed(
                "Authorization header must be 'Bearer <access_token>'."
            )

        token_value = auth_header[len("Bearer "):]
        access_token = get_access_token(filters={"token": token_value})

        if not access_token:
            raise AuthenticationFailed("Invalid access_token.")
        if access_token.is_expired:
            raise AuthenticationFailed("access_token has expired.")

        user = access_token.user
        return Response(
            {
                "sub": str(user.id),
                "name": user.name,
                "phone": str(user.phone) if user.phone else "",
            }
        )
