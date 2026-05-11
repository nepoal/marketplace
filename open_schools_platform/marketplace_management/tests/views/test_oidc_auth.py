from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from open_schools_platform.marketplace_management.tests.utils import (
    create_test_app,
    create_test_app_launch,
    create_test_installation,
    create_test_oidc_client_with_secret,
)
from open_schools_platform.user_management.users.tests.utils import create_test_user

NS = "api:marketplace-management:marketplace"
REDIRECT_URI = "https://testapp.example.com/oidc/callback"


class OidcAuthApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse(f"{NS}:marketplace-oidc-auth")
        self.user = create_test_user()
        self.app = create_test_app(with_url=True)
        create_test_installation(app=self.app, user=self.user)
        self.oidc_client, _ = create_test_oidc_client_with_secret(
            app=self.app, redirect_uris=[REDIRECT_URI]
        )
        self.client_id = self.oidc_client.client_id
        self.launch = create_test_app_launch(app=self.app, user=self.user)

    def _params(self, **overrides):
        p = {
            "client_id": self.client_id,
            "scope": "openid",
            "response_type": "code id_token",
            "redirect_uri": REDIRECT_URI,
            "launch_token": self.launch.launch_token,
            "nonce": "test-nonce-123",
        }
        p.update(overrides)
        return p

    def test_successful_authorize_returns_302(self):
        response = self.client.get(self.url, self._params())
        self.assertEqual(302, response.status_code)

    def test_location_header_contains_code_and_id_token(self):
        response = self.client.get(self.url, self._params())
        location = response.headers["Location"]
        self.assertIn(REDIRECT_URI, location)
        self.assertIn("code=", location)
        self.assertIn("id_token=", location)

    def test_missing_client_id_returns_400(self):
        params = self._params()
        del params["client_id"]
        response = self.client.get(self.url, params)
        self.assertEqual(400, response.status_code)

    def test_missing_launch_token_returns_400(self):
        params = self._params()
        del params["launch_token"]
        response = self.client.get(self.url, params)
        self.assertEqual(400, response.status_code)

    def test_missing_redirect_uri_returns_400(self):
        params = self._params()
        del params["redirect_uri"]
        response = self.client.get(self.url, params)
        self.assertEqual(400, response.status_code)

    def test_missing_scope_returns_400(self):
        params = self._params()
        del params["scope"]
        response = self.client.get(self.url, params)
        self.assertEqual(400, response.status_code)

    def test_unregistered_redirect_uri_returns_403(self):
        response = self.client.get(
            self.url, self._params(redirect_uri="https://evil.example.com/callback")
        )
        self.assertEqual(403, response.status_code)

    def test_invalid_response_type_returns_400(self):
        response = self.client.get(self.url, self._params(response_type="token"))
        self.assertEqual(400, response.status_code)

    def test_scope_without_openid_returns_400(self):
        response = self.client.get(self.url, self._params(scope="profile"))
        self.assertEqual(400, response.status_code)

    def test_expired_launch_token_returns_400(self):
        self.launch.token_exp = timezone.now() - timezone.timedelta(minutes=10)
        self.launch.save(update_fields=["token_exp"])
        response = self.client.get(self.url, self._params())
        self.assertEqual(400, response.status_code)

    def test_used_launch_token_returns_400(self):
        self.client.get(self.url, self._params())
        response = self.client.get(self.url, self._params())
        self.assertEqual(400, response.status_code)

    def test_anonymous_access_allowed(self):
        response = self.client.get(self.url, self._params())
        self.assertEqual(302, response.status_code)
