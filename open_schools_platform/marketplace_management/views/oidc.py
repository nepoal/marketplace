from django.http import HttpResponse
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from open_schools_platform.api.swagger_tags import SwaggerTags
from open_schools_platform.marketplace_management.oidc_server import authorization_server
from open_schools_platform.marketplace_management.selectors import get_access_token
from open_schools_platform.marketplace_management.serializers import (
    OidcTokenResponseSerializer,
    OidcUserInfoSerializer,
)
from open_schools_platform.marketplace_management.services import initiate_oidc_auth
from open_schools_platform.user_management.users.serializers import GetUserProfilesSerializer

TAGS = [SwaggerTags.MARKETPLACE_MANAGEMENT]


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
            {"user": GetUserProfilesSerializer(user, context={"request": request}).data}
        )
