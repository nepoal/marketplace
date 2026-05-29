from urllib.parse import urlencode

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from open_schools_platform.marketplace_management.models import (
    OidcAccessToken,
    OidcAuthorizationCode,
)
from open_schools_platform.marketplace_management.tests.utils import (
    create_test_app,
    create_test_app_launch,
    create_test_installation,
    create_test_oidc_client_with_secret,
)
from open_schools_platform.user_management.users.tests.utils import create_test_user

NS = "api:marketplace-management:marketplace"
REDIRECT_URI = "https://testapp.example.com/oidc/callback"


class OidcUserInfoApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.userinfo_url = reverse(f"{NS}:marketplace-oidc-userinfo")
        self.auth_url = reverse(f"{NS}:marketplace-oidc-auth")
        self.token_url = reverse(f"{NS}:marketplace-oidc-token")
        self.user = create_test_user()
        self.app = create_test_app(with_url=True)
        create_test_installation(app=self.app, user=self.user)
        self.oidc_client, self.raw_secret = create_test_oidc_client_with_secret(
            app=self.app, redirect_uris=[REDIRECT_URI]
        )
        self.client_id = self.oidc_client.client_id

    def _obtain_access_token(self) -> str:
        launch = create_test_app_launch(app=self.app, user=self.user)
        self.client.get(
            self.auth_url,
            {
                "client_id": self.client_id,
                "scope": "openid",
                "response_type": "code id_token",
                "redirect_uri": REDIRECT_URI,
                "launch_token": launch.launch_token,
                "nonce": "nonce-userinfo",
            },
        )
        auth_code = OidcAuthorizationCode.objects.filter(
            client=self.oidc_client
        ).first()
        token_response = self.client.post(
            self.token_url,
            urlencode(
                {
                    "grant_type": "authorization_code",
                    "code": auth_code.code,
                    "redirect_uri": REDIRECT_URI,
                    "client_id": self.client_id,
                    "client_secret": self.raw_secret,
                }
            ),
            content_type="application/x-www-form-urlencoded",
        )
        return token_response.data["access_token"]

    def test_successful_userinfo(self):
        access_token = self._obtain_access_token()
        response = self.client.get(
            self.userinfo_url, HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )
        self.assertEqual(200, response.status_code)
        self.assertIn("user", response.data)

    def test_userinfo_contains_user_id(self):
        access_token = self._obtain_access_token()
        response = self.client.get(
            self.userinfo_url, HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )
        self.assertEqual(str(self.user.id), response.data["user"]["id"])

    def test_missing_auth_header_returns_401(self):
        response = self.client.get(self.userinfo_url)
        self.assertEqual(401, response.status_code)

    def test_malformed_auth_header_returns_401(self):
        response = self.client.get(
            self.userinfo_url, HTTP_AUTHORIZATION="Token some-token"
        )
        self.assertEqual(401, response.status_code)

    def test_invalid_token_returns_401(self):
        response = self.client.get(
            self.userinfo_url, HTTP_AUTHORIZATION="Bearer completely-invalid-token"
        )
        self.assertEqual(401, response.status_code)

    def test_expired_token_returns_401(self):
        access_token = self._obtain_access_token()
        token_obj = OidcAccessToken.objects.get(token=access_token)
        token_obj.expires_at = timezone.now() - timezone.timedelta(hours=2)
        token_obj.save(update_fields=["expires_at"])
        response = self.client.get(
            self.userinfo_url, HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )
        self.assertEqual(401, response.status_code)
