import secrets
import uuid

import safedelete
from django.contrib.auth.hashers import make_password, check_password
from django.db import models
from django.utils import timezone

from open_schools_platform.common.models import BaseModel, BaseManager
from open_schools_platform.user_management.users.models import User
from open_schools_platform.marketplace_management.models.app import App


class OidcClientManager(BaseManager):
    def create_client(self, app, redirect_uris: list):
        client_id = f"marketplace-{secrets.token_urlsafe(24)}"
        client_secret = secrets.token_urlsafe(48)
        client = self.model(
            app=app,
            client_id=client_id,
            client_secret_hash=make_password(client_secret),
            redirect_uris=redirect_uris,
        )
        client.full_clean()
        client.save(using=self._db)
        return client, client_secret


class OidcClient(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    app = models.OneToOneField(
        App, on_delete=models.CASCADE, related_name="oidc_client"
    )
    client_id = models.CharField(max_length=128, unique=True)
    client_secret_hash = models.CharField(max_length=256)
    redirect_uris = models.JSONField(default=list, blank=True)

    objects = OidcClientManager()

    def verify_secret(self, secret: str) -> bool:
        return check_password(secret, self.client_secret_hash)

    def get_client_id(self) -> str:
        return self.client_id

    def get_default_redirect_uri(self) -> str:
        return self.redirect_uris[0] if self.redirect_uris else ""

    def get_allowed_scope(self, scope: str) -> str:
        """Return the intersection of the requested scope and the supported scopes.

        Currently only 'openid' is supported; other values are silently dropped.
        """
        allowed = {"openid"}
        return " ".join(s for s in scope.split() if s in allowed)

    def check_redirect_uri(self, redirect_uri: str) -> bool:
        return redirect_uri in self.redirect_uris

    def check_client_secret(self, client_secret: str) -> bool:
        return self.verify_secret(client_secret)

    def check_endpoint_auth_method(self, method: str, endpoint: str) -> bool:
        return method in ("client_secret_basic", "client_secret_post")

    def check_grant_type(self, grant_type: str) -> bool:
        return grant_type in ("authorization_code", "refresh_token")

    def check_response_type(self, response_type: str) -> bool:
        return all(rt in {"code", "id_token"} for rt in response_type.split())

    def __str__(self):
        return f"OidcClient({self.client_id[:20]}...)"


class OidcAuthorizationCode(BaseModel):
    _safedelete_policy = safedelete.config.HARD_DELETE

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    code = models.CharField(max_length=256, unique=True)
    client = models.ForeignKey(
        OidcClient, on_delete=models.CASCADE, related_name="auth_codes"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="oidc_auth_codes"
    )
    redirect_uri = models.CharField(max_length=500)
    nonce = models.CharField(max_length=256, blank=True)
    scope = models.CharField(max_length=200, default="openid")
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    objects = BaseManager()

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    def get_redirect_uri(self) -> str:
        return self.redirect_uri

    def get_scope(self) -> str:
        return self.scope

    def get_auth_time(self) -> int:
        return int(self.created_at.timestamp())

    def get_nonce(self) -> str:
        return self.nonce

    def __str__(self):
        return f"AuthCode({self.code[:16]}...)"


class OidcAccessToken(BaseModel):
    _safedelete_policy = safedelete.config.HARD_DELETE

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    token = models.CharField(max_length=256, unique=True)
    client = models.ForeignKey(
        OidcClient, on_delete=models.CASCADE, related_name="access_tokens"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="oidc_access_tokens"
    )
    scope = models.CharField(max_length=200, default="openid")
    expires_at = models.DateTimeField()

    objects = BaseManager()

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def expires_in(self):
        """Return remaining lifetime in seconds, clamped to zero when expired."""
        delta = self.expires_at - timezone.now()
        return max(0, int(delta.total_seconds()))

    def get_client_id(self) -> str:
        return self.client.client_id

    def get_scope(self) -> str:
        return self.scope

    def get_expires_in(self) -> int:
        return max(0, int((self.expires_at - timezone.now()).total_seconds()))

    def get_expires_at(self) -> int:
        return int(self.expires_at.timestamp())

    def is_revoked(self) -> bool:
        return False

    def __str__(self):
        return f"AccessToken({self.token[:16]}...)"


class OidcRefreshToken(BaseModel):
    _safedelete_policy = safedelete.config.HARD_DELETE

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    token = models.CharField(max_length=256, unique=True)
    client = models.ForeignKey(
        OidcClient, on_delete=models.CASCADE, related_name="refresh_tokens"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="oidc_refresh_tokens"
    )
    access_token = models.OneToOneField(
        OidcAccessToken,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="refresh_token",
    )
    expires_at = models.DateTimeField()

    objects = BaseManager()

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    def get_scope(self) -> str:
        """Return the scope from the linked access token, falling back to 'openid'."""
        return self.access_token.scope if self.access_token else "openid"

    def get_client_id(self) -> str:
        return self.client.client_id

    def check_client(self, client) -> bool:
        """Check that this token belongs to the given client.

        Called by authlib during refresh token validation.
        """
        return self.client_id == client.pk

    def __str__(self):
        return f"RefreshToken({self.token[:16]}...)"
