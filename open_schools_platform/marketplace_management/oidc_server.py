import time

from authlib.integrations.django_oauth2 import AuthorizationServer
from authlib.jose import jwt as authlib_jwt
from authlib.oauth2.rfc6749 import grants
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from open_schools_platform.marketplace_management.constants import (
    ACCESS_TOKEN_TTL,
    REFRESH_TOKEN_TTL,
)


def get_issuer() -> str:
    return getattr(settings, "MARKETPLACE_OIDC_ISSUER", "https://platform.local")


def generate_id_token(
    user, client, nonce: str = "", ttl: int = ACCESS_TOKEN_TTL
) -> str:
    """Generate a signed HS256 JWT id_token with standard OIDC claims.

    Nonce is included only when provided. SECRET_KEY is encoded to bytes
    if it arrives as a string, since authlib requires bytes.
    """
    now = int(time.time())
    header = {"alg": "HS256"}
    payload = {
        "iss": get_issuer(),
        "sub": str(user.id),
        "aud": client.client_id,
        "exp": now + ttl,
        "iat": now,
        "name": user.name,
        "phone": str(user.phone) if user.phone else "",
    }
    if nonce:
        payload["nonce"] = nonce

    key = settings.SECRET_KEY
    if isinstance(key, str):
        key = key.encode("utf-8")

    token = authlib_jwt.encode(header, payload, key)
    return token.decode("utf-8") if isinstance(token, bytes) else str(token)


class AuthorizationCodeGrant(grants.AuthorizationCodeGrant):
    """Authorization Code grant that stores codes in the DB and appends id_token to the response."""

    TOKEN_ENDPOINT_AUTH_METHODS = ["client_secret_basic", "client_secret_post"]

    def query_authorization_code(self, code: str, client):
        from open_schools_platform.marketplace_management.models import (
            OidcAuthorizationCode,
        )

        try:
            auth_code = OidcAuthorizationCode.objects.select_related("user").get(
                code=code,
                client=client,
            )
            if not auth_code.is_used and not auth_code.is_expired:
                return auth_code
        except OidcAuthorizationCode.DoesNotExist:
            pass
        return None

    def delete_authorization_code(self, authorization_code):
        authorization_code.is_used = True
        authorization_code.save(update_fields=["is_used"])

    def authenticate_user(self, authorization_code):
        return authorization_code.user

    def create_token_response(self):
        """Extend the parent response with id_token when the grant succeeds."""
        status, token, headers = super().create_token_response()
        if status != 200 or not getattr(self.request, "authorization_code", None):
            return status, token, headers
        nonce = self.request.authorization_code.get_nonce()
        token["id_token"] = generate_id_token(
            user=self.request.user,
            client=self.request.client,
            nonce=nonce,
        )
        return status, token, headers


class RefreshTokenGrant(grants.RefreshTokenGrant):
    """Refresh Token grant that reuses the same refresh token (no rotation) and appends id_token."""

    TOKEN_ENDPOINT_AUTH_METHODS = ["client_secret_basic", "client_secret_post"]
    INCLUDE_NEW_REFRESH_TOKEN = False

    def authenticate_refresh_token(self, refresh_token: str):
        from open_schools_platform.marketplace_management.models import OidcRefreshToken

        try:
            token = OidcRefreshToken.objects.select_related(
                "client", "user", "access_token"
            ).get(token=refresh_token)
            if not token.is_expired:
                return token
        except OidcRefreshToken.DoesNotExist:
            pass
        return None

    def authenticate_user(self, credential):
        return credential.user

    def revoke_old_credential(self, credential):
        # FK updated by save_token — nothing to revoke
        pass

    def create_token_response(self):
        """Extend the parent response with the original refresh_token and a fresh id_token."""
        status, token, headers = super().create_token_response()
        if status != 200 or not getattr(self.request, "refresh_token", None):
            return status, token, headers
        token["refresh_token"] = self.request.refresh_token.token
        token["id_token"] = generate_id_token(
            user=self.request.user,
            client=self.request.client,
        )
        return status, token, headers


class MarketplaceAuthorizationServer(AuthorizationServer):
    """Authorization server that stores tokens in the DB instead of using the default authlib model."""

    def __init__(self):
        from open_schools_platform.marketplace_management.models import OidcClient

        super().__init__(client_model=OidcClient, token_model=None)

    def generate_token(
        self,
        grant_type,
        client,
        user=None,
        scope=None,
        expires_in=None,
        include_refresh_token=True,
    ):
        import secrets

        token = {
            "token_type": "Bearer",
            "access_token": secrets.token_urlsafe(42),
            "expires_in": ACCESS_TOKEN_TTL,
            "scope": scope or "openid",
        }
        if include_refresh_token:
            token["refresh_token"] = secrets.token_urlsafe(48)
        return token

    def query_client(self, client_id: str):
        from open_schools_platform.marketplace_management.models import OidcClient

        try:
            return OidcClient.objects.get(client_id=client_id)
        except OidcClient.DoesNotExist:
            return None

    def save_token(self, token: dict, request):
        """Save access and refresh tokens to the DB.

        For authorization_code grant a new refresh token is created.
        For refresh_token grant the existing token is reused — only its access_token FK is updated.
        """
        from open_schools_platform.marketplace_management.models import (
            OidcAccessToken,
            OidcRefreshToken,
        )

        now = timezone.now()

        with transaction.atomic():
            access_token_obj = OidcAccessToken.objects.create(
                token=token["access_token"],
                client=request.client,
                user=request.user,
                scope=token.get("scope", "openid"),
                expires_at=now + timezone.timedelta(seconds=token["expires_in"]),
            )

            if "refresh_token" in token:
                OidcRefreshToken.objects.create(
                    token=token["refresh_token"],
                    client=request.client,
                    user=request.user,
                    access_token=access_token_obj,
                    expires_at=now + timezone.timedelta(seconds=REFRESH_TOKEN_TTL),
                )
            elif isinstance(getattr(request, "refresh_token", None), OidcRefreshToken):
                request.refresh_token.access_token = access_token_obj
                request.refresh_token.save(update_fields=["access_token"])

        return access_token_obj


authorization_server = MarketplaceAuthorizationServer()
authorization_server.register_grant(AuthorizationCodeGrant)
authorization_server.register_grant(RefreshTokenGrant)
