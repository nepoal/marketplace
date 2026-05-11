from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from open_schools_platform.marketplace_management.models import OidcAuthorizationCode
from open_schools_platform.marketplace_management.services.oidc import (
    initiate_oidc_auth,
)
from open_schools_platform.marketplace_management.tests.utils import (
    create_test_app,
    create_test_app_launch,
    create_test_installation,
    create_test_oidc_client_with_secret,
)
from open_schools_platform.user_management.users.tests.utils import create_test_user


class InitiateOidcAuthTests(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.redirect_uri = "https://testapp.example.com/oidc/callback"
        self.app = create_test_app(with_url=True)
        create_test_installation(app=self.app, user=self.user)
        self.oidc_client, self.raw_secret = create_test_oidc_client_with_secret(
            app=self.app, redirect_uris=[self.redirect_uri]
        )
        self.client_id = self.oidc_client.client_id
        self.launch = create_test_app_launch(app=self.app, user=self.user)

    def _do_auth(self, **overrides):
        params = dict(
            client_id=self.client_id,
            redirect_uri=self.redirect_uri,
            scope="openid",
            response_type="code id_token",
            nonce="test-nonce-123",
            launch_token=self.launch.launch_token,
        )
        params.update(overrides)
        return initiate_oidc_auth(**params)

    def test_successful_auth_returns_redirect_url_and_code(self):
        redirect_url, code, id_token = self._do_auth()
        self.assertIn(self.redirect_uri, redirect_url)
        self.assertIn(f"code={code}", redirect_url)
        self.assertIn(f"id_token={id_token}", redirect_url)
        self.assertEqual(1, OidcAuthorizationCode.objects.count())

    def test_auth_code_linked_to_correct_user(self):
        _, code, _ = self._do_auth()
        auth_code = OidcAuthorizationCode.objects.get(code=code)
        self.assertEqual(self.user, auth_code.user)

    def test_launch_token_marked_as_used_after_auth(self):
        self._do_auth()
        self.launch.refresh_from_db()
        self.assertTrue(self.launch.is_used)

    def test_nonce_stored_in_auth_code(self):
        _, code, _ = self._do_auth(nonce="my-unique-nonce")
        auth_code = OidcAuthorizationCode.objects.get(code=code)
        self.assertEqual("my-unique-nonce", auth_code.get_nonce())

    def test_unknown_client_id_raises_error(self):
        with self.assertRaises(Exception):
            self._do_auth(client_id="unknown-client-id")

    def test_unregistered_redirect_uri_raises_permission_denied(self):
        with self.assertRaises(PermissionDenied):
            self._do_auth(redirect_uri="https://evil.example.com/callback")

    def test_invalid_response_type_raises_validation_error(self):
        with self.assertRaises(ValidationError) as ctx:
            self._do_auth(response_type="token")
        self.assertIn("code id_token", str(ctx.exception))

    def test_scope_without_openid_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            self._do_auth(scope="profile")

    def test_expired_launch_token_raises_validation_error(self):
        self.launch.token_exp = timezone.now() - timezone.timedelta(minutes=10)
        self.launch.save(update_fields=["token_exp"])
        with self.assertRaises(ValidationError) as ctx:
            self._do_auth()
        self.assertIn("expired", str(ctx.exception))

    def test_used_launch_token_raises_validation_error(self):
        self._do_auth()
        with self.assertRaises(ValidationError) as ctx:
            initiate_oidc_auth(
                client_id=self.client_id,
                redirect_uri=self.redirect_uri,
                scope="openid",
                response_type="code id_token",
                nonce="nonce2",
                launch_token=self.launch.launch_token,
            )
        self.assertIn("already been used", str(ctx.exception))

    def test_launch_token_from_other_app_raises_permission_denied(self):
        other_redirect = "https://other.example.com/callback"
        other_app = create_test_app(name="Other App", with_url=True)
        create_test_installation(app=other_app, user=self.user)
        create_test_oidc_client_with_secret(
            app=other_app, redirect_uris=[other_redirect]
        )
        other_launch = create_test_app_launch(app=other_app, user=self.user)
        with self.assertRaises(PermissionDenied):
            self._do_auth(launch_token=other_launch.launch_token)
