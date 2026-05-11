import secrets

from django.test import TestCase
from django.utils import timezone

from open_schools_platform.marketplace_management.models import (
    OidcAccessToken,
    OidcAuthorizationCode,
    OidcRefreshToken,
)
from open_schools_platform.marketplace_management.selectors.oidc import (
    get_access_token,
    get_auth_code,
    get_oidc_client,
    get_refresh_token,
)
from open_schools_platform.marketplace_management.tests.utils import (
    create_test_app,
    create_test_oidc_client_with_secret,
)
from open_schools_platform.user_management.users.tests.utils import create_test_user


def _make_auth_code(client, user):
    return OidcAuthorizationCode.objects.create(
        code=secrets.token_urlsafe(32),
        client=client,
        user=user,
        redirect_uri="https://example.com/callback",
        expires_at=timezone.now() + timezone.timedelta(minutes=5),
    )


def _make_access_token(client, user):
    return OidcAccessToken.objects.create(
        token=secrets.token_urlsafe(32),
        client=client,
        user=user,
        expires_at=timezone.now() + timezone.timedelta(hours=1),
    )


def _make_refresh_token(client, user, access_token):
    return OidcRefreshToken.objects.create(
        token=secrets.token_urlsafe(32),
        client=client,
        user=user,
        access_token=access_token,
        expires_at=timezone.now() + timezone.timedelta(days=30),
    )


class GetOidcClientSelectorTests(TestCase):
    def setUp(self):
        self.app = create_test_app(with_url=True)
        self.client_obj, _ = create_test_oidc_client_with_secret(app=self.app)

    def test_get_by_client_id(self):
        result = get_oidc_client(filters={"client_id": self.client_obj.client_id})
        self.assertEqual(self.client_obj, result)

    def test_get_by_id(self):
        result = get_oidc_client(filters={"id": self.client_obj.id})
        self.assertEqual(self.client_obj, result)

    def test_nonexistent_returns_none(self):
        result = get_oidc_client(filters={"client_id": "nonexistent"})
        self.assertIsNone(result)


class GetAuthCodeSelectorTests(TestCase):
    def setUp(self):
        self.app = create_test_app(with_url=True)
        self.oidc_client, _ = create_test_oidc_client_with_secret(app=self.app)
        self.user = create_test_user()
        self.auth_code = _make_auth_code(self.oidc_client, self.user)

    def test_get_by_code(self):
        result = get_auth_code(filters={"code": self.auth_code.code})
        self.assertEqual(self.auth_code, result)

    def test_nonexistent_returns_none(self):
        result = get_auth_code(filters={"code": "nonexistent"})
        self.assertIsNone(result)


class GetAccessTokenSelectorTests(TestCase):
    def setUp(self):
        self.app = create_test_app(with_url=True)
        self.oidc_client, _ = create_test_oidc_client_with_secret(app=self.app)
        self.user = create_test_user()
        self.access_token = _make_access_token(self.oidc_client, self.user)

    def test_get_by_token(self):
        result = get_access_token(filters={"token": self.access_token.token})
        self.assertEqual(self.access_token, result)

    def test_nonexistent_returns_none(self):
        result = get_access_token(filters={"token": "nonexistent"})
        self.assertIsNone(result)


class GetRefreshTokenSelectorTests(TestCase):
    def setUp(self):
        self.app = create_test_app(with_url=True)
        self.oidc_client, _ = create_test_oidc_client_with_secret(app=self.app)
        self.user = create_test_user()
        access_token = _make_access_token(self.oidc_client, self.user)
        self.refresh_token = _make_refresh_token(self.oidc_client, self.user, access_token)

    def test_get_by_token(self):
        result = get_refresh_token(filters={"token": self.refresh_token.token})
        self.assertEqual(self.refresh_token, result)

    def test_nonexistent_returns_none(self):
        result = get_refresh_token(filters={"token": "nonexistent"})
        self.assertIsNone(result)
