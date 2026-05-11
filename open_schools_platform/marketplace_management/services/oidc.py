import logging
import secrets
from typing import Tuple

from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied

logger = logging.getLogger("marketplace_management")

from open_schools_platform.marketplace_management.constants import AUTH_CODE_TTL
from open_schools_platform.marketplace_management.models import (
    App,
    OidcClient,
    OidcAuthorizationCode,
)


def create_oidc_client_for_app(
    *, app: App, redirect_uris: list
) -> Tuple[OidcClient, str]:
    if hasattr(app, "oidc_client"):
        raise ValidationError("This app already has OIDC credentials.")
    client, raw_secret = OidcClient.objects.create_client(
        app=app, redirect_uris=redirect_uris
    )
    return client, raw_secret


def update_oidc_redirect_uris(
    *, oidc_client: OidcClient, redirect_uris: list
) -> OidcClient:
    oidc_client.redirect_uris = redirect_uris
    oidc_client.save(update_fields=["redirect_uris", "updated_at"])
    return oidc_client


def initiate_oidc_auth(
    *,
    client_id: str,
    redirect_uri: str,
    scope: str,
    response_type: str,
    nonce: str,
    launch_token: str,
) -> Tuple[str, str, str]:
    """Run the OIDC authorization flow using a launch_token instead of a browser session.

    The launch_token identifies the user without relying on session cookies,
    which makes it suitable for iframe-embedded apps.
    Returns a tuple of (redirect_url, code, id_token).
    """
    from open_schools_platform.marketplace_management.oidc_server import (
        generate_id_token,
    )
    from open_schools_platform.marketplace_management.selectors import (
        get_oidc_client,
        get_app_launch,
    )

    client = get_oidc_client(
        filters={"client_id": client_id},
        empty_exception=True,
        empty_message="Unknown client_id.",
    )

    if not client.check_redirect_uri(redirect_uri):
        logger.warning("Invalid redirect_uri: client_id=%s uri=%s", client_id, redirect_uri)
        raise PermissionDenied("redirect_uri is not registered for this client.")

    if not client.check_response_type(response_type):
        raise ValidationError(
            f"Unsupported response_type: '{response_type}'. Expected 'code id_token'."
        )

    if "openid" not in scope.split():
        raise ValidationError("scope must include 'openid'.")

    launch = get_app_launch(
        filters={"launch_token": launch_token},
        empty_exception=True,
        empty_message="Invalid or missing launch_token.",
    )

    if launch.is_expired:
        logger.warning("Expired launch_token: client_id=%s", client_id)
        raise ValidationError("launch_token has expired.")

    if launch.is_used:
        logger.warning("Reused launch_token: client_id=%s", client_id)
        raise ValidationError("launch_token has already been used.")

    if launch.app.oidc_client.client_id != client_id:
        logger.warning(
            "launch_token client mismatch: expected=%s got=%s",
            client_id,
            launch.app.oidc_client.client_id,
        )
        raise PermissionDenied("launch_token does not belong to this client.")

    user = launch.user
    code = secrets.token_urlsafe(48)

    OidcAuthorizationCode.objects.create(
        code=code,
        client=client,
        user=user,
        redirect_uri=redirect_uri,
        nonce=nonce,
        scope=scope,
        expires_at=timezone.now() + timezone.timedelta(seconds=AUTH_CODE_TTL),
    )

    launch.is_used = True
    launch.save(update_fields=["is_used"])

    id_token = generate_id_token(user=user, client=client, nonce=nonce)

    logger.info("Auth code issued: client_id=%s user_id=%s", client_id, user.id)
    fragment = f"code={code}&id_token={id_token}"
    return f"{redirect_uri}#{fragment}", code, id_token
