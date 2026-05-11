from django.test import TestCase
from rest_framework.exceptions import ValidationError

from open_schools_platform.marketplace_management.services.oidc import (
    create_oidc_client_for_app,
    update_oidc_redirect_uris,
)
from open_schools_platform.marketplace_management.tests.utils import (
    create_test_app,
    create_test_oidc_client,
)


class CreateOidcClientTests(TestCase):
    def test_successful_client_creation(self):
        app = create_test_app()
        client, raw_secret = create_oidc_client_for_app(
            app=app, redirect_uris=["https://myapp.example.com/callback"]
        )
        self.assertTrue(client.client_id.startswith("marketplace-"))
        self.assertTrue(client.verify_secret(raw_secret))
        self.assertEqual(["https://myapp.example.com/callback"], client.redirect_uris)

    def test_raw_secret_is_not_stored_in_plaintext(self):
        app = create_test_app()
        client, raw_secret = create_oidc_client_for_app(
            app=app, redirect_uris=["https://myapp.example.com/callback"]
        )
        self.assertNotEqual(raw_secret, client.client_secret_hash)

    def test_duplicate_client_for_same_app_raises_error(self):
        app = create_test_app()
        create_oidc_client_for_app(
            app=app, redirect_uris=["https://myapp.example.com/callback"]
        )
        with self.assertRaises(ValidationError):
            create_oidc_client_for_app(
                app=app, redirect_uris=["https://other.com/callback"]
            )

    def test_multiple_redirect_uris_stored(self):
        app = create_test_app()
        uris = [
            "https://myapp.example.com/callback",
            "https://myapp.example.com/callback2",
        ]
        client, _ = create_oidc_client_for_app(app=app, redirect_uris=uris)
        self.assertEqual(uris, client.redirect_uris)


class UpdateOidcRedirectUrisTests(TestCase):
    def test_successful_uri_update(self):
        app = create_test_app()
        client = create_test_oidc_client(app=app)
        new_uris = ["https://new.example.com/callback"]
        updated = update_oidc_redirect_uris(oidc_client=client, redirect_uris=new_uris)
        self.assertEqual(new_uris, updated.redirect_uris)

    def test_replace_all_uris_with_empty_list(self):
        app = create_test_app()
        client = create_test_oidc_client(
            app=app, redirect_uris=["https://old.example.com/callback"]
        )
        update_oidc_redirect_uris(oidc_client=client, redirect_uris=[])
        client.refresh_from_db()
        self.assertEqual([], client.redirect_uris)
