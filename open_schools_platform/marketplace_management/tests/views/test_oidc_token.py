from urllib.parse import urlencode

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from open_schools_platform.marketplace_management.models import OidcAccessToken, OidcAuthorizationCode
from open_schools_platform.marketplace_management.tests.utils import (
    create_test_app,
    create_test_app_launch,
    create_test_installation,
    create_test_oidc_client_with_secret,
)
from open_schools_platform.user_management.users.tests.utils import create_test_user

NS = "api:marketplace-management:marketplace"
REDIRECT_URI = "https://testapp.example.com/oidc/callback"


class OidcTokenApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.token_url = reverse(f"{NS}:marketplace-oidc-token")
        self.auth_url = reverse(f"{NS}:marketplace-oidc-auth")
        self.user = create_test_user()
        self.app = create_test_app(with_url=True)
        create_test_installation(app=self.app, user=self.user)
        self.oidc_client, self.raw_secret = create_test_oidc_client_with_secret(
            app=self.app, redirect_uris=[REDIRECT_URI]
        )
        self.client_id = self.oidc_client.client_id
        self.launch = create_test_app_launch(app=self.app, user=self.user)

    def _get_auth_code(self):
        self.client.get(self.auth_url, {
            "client_id": self.client_id,
            "scope": "openid",
            "response_type": "code id_token",
            "redirect_uri": REDIRECT_URI,
            "launch_token": self.launch.launch_token,
            "nonce": "nonce-for-token-test",
        })
        return OidcAuthorizationCode.objects.filter(client=self.oidc_client).first()

    def _post_token(self, data: dict):
        return self.client.post(
            self.token_url,
            urlencode(data),
            content_type="application/x-www-form-urlencoded",
        )

    def test_exchange_code_for_tokens(self):
        auth_code = self._get_auth_code()
        response = self._post_token({
            "grant_type": "authorization_code",
            "code": auth_code.code,
            "redirect_uri": REDIRECT_URI,
            "client_id": self.client_id,
            "client_secret": self.raw_secret,
        })
        self.assertEqual(200, response.status_code)
        self.assertIn("access_token", response.data)
        self.assertIn("refresh_token", response.data)
        self.assertIn("id_token", response.data)
        self.assertEqual("Bearer", response.data["token_type"])
        self.assertEqual("openid", response.data["scope"])

    def test_access_token_saved_in_db(self):
        auth_code = self._get_auth_code()
        self._post_token({
            "grant_type": "authorization_code",
            "code": auth_code.code,
            "redirect_uri": REDIRECT_URI,
            "client_id": self.client_id,
            "client_secret": self.raw_secret,
        })
        self.assertEqual(1, OidcAccessToken.objects.count())

    def test_refresh_token_grant(self):
        auth_code = self._get_auth_code()
        token_response = self._post_token({
            "grant_type": "authorization_code",
            "code": auth_code.code,
            "redirect_uri": REDIRECT_URI,
            "client_id": self.client_id,
            "client_secret": self.raw_secret,
        })
        refresh_token = token_response.data["refresh_token"]

        refresh_response = self._post_token({
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
            "client_secret": self.raw_secret,
        })
        self.assertEqual(200, refresh_response.status_code)
        self.assertIn("access_token", refresh_response.data)
        self.assertIn("id_token", refresh_response.data)

    def test_refresh_token_stays_the_same(self):
        auth_code = self._get_auth_code()
        token_response = self._post_token({
            "grant_type": "authorization_code",
            "code": auth_code.code,
            "redirect_uri": REDIRECT_URI,
            "client_id": self.client_id,
            "client_secret": self.raw_secret,
        })
        original_refresh_token = token_response.data["refresh_token"]

        refresh_response = self._post_token({
            "grant_type": "refresh_token",
            "refresh_token": original_refresh_token,
            "client_id": self.client_id,
            "client_secret": self.raw_secret,
        })
        self.assertEqual(original_refresh_token, refresh_response.data["refresh_token"])

    def test_invalid_auth_code_returns_error(self):
        response = self._post_token({
            "grant_type": "authorization_code",
            "code": "completely-invalid-code",
            "redirect_uri": REDIRECT_URI,
            "client_id": self.client_id,
            "client_secret": self.raw_secret,
        })
        self.assertNotEqual(200, response.status_code)

    def test_wrong_client_secret_returns_error(self):
        auth_code = self._get_auth_code()
        response = self._post_token({
            "grant_type": "authorization_code",
            "code": auth_code.code,
            "redirect_uri": REDIRECT_URI,
            "client_id": self.client_id,
            "client_secret": "wrong-secret",
        })
        self.assertNotEqual(200, response.status_code)
