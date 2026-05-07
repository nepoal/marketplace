import secrets
from typing import Tuple

from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied

from open_schools_platform.common.services import model_update
from open_schools_platform.marketplace_management.models import (
    App,
    AppVersion,
    AppUrl,
    Category,
    Installation,
    Review,
    Payment,
    OidcClient,
    OidcAuthorizationCode,
    AppLaunch,
    ModeratorProfile,
)
from open_schools_platform.user_management.users.models import User

AUTH_CODE_TTL = 300  # 5 minutes (must match oidc_server.AUTH_CODE_TTL)
LAUNCH_TOKEN_TTL = 300  # 5 minutes


def create_category(*, name: str) -> Category:
    return Category.objects.create_category(name=name)


def update_category(*, category: Category, data: dict) -> Category:
    category, _ = model_update(instance=category, fields=["name"], data=data)
    return category


def create_app(
    *,
    name: str,
    short_description: str = "",
    description: str = "",
    category: Category = None,
    icon_url: str = "",
    screenshots: list = None,
    is_free: bool = True,
    amount=None,
    currency: str = "RUB",
) -> App:
    return App.objects.create_app(
        name=name,
        short_description=short_description,
        description=description,
        category=category,
        icon_url=icon_url,
        screenshots=screenshots or [],
        is_free=is_free,
        amount=amount,
        currency=currency,
    )


def update_app(*, app: App, data: dict) -> App:
    updatable = [
        "name",
        "short_description",
        "description",
        "status",
        "icon_url",
        "screenshots",
        "category",
        "is_free",
        "amount",
        "currency",
    ]
    app, _ = model_update(instance=app, fields=updatable, data=data)
    return app


def create_app_version(*, app: App, version: str, description: str = "") -> AppVersion:
    return AppVersion.objects.create_version(
        app=app, version=version, description=description
    )


def create_app_url(
    *, app: App, base_url: str, launch_path: str = "/", health_check_path: str = ""
) -> AppUrl:
    if hasattr(app, "url_config"):
        raise ValidationError("This app already has a URL configuration.")
    return AppUrl.objects.create_url(
        app=app,
        base_url=base_url,
        launch_path=launch_path,
        health_check_path=health_check_path,
    )


def update_app_url(*, app_url: AppUrl, data: dict) -> AppUrl:
    app_url, _ = model_update(
        instance=app_url,
        fields=["base_url", "launch_path", "health_check_path"],
        data=data,
    )
    return app_url


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
        raise PermissionDenied("redirect_uri is not registered for this client.")

    if "openid" not in scope.split():
        raise ValidationError("scope must include 'openid'.")

    launch = get_app_launch(
        filters={"launch_token": launch_token},
        empty_exception=True,
        empty_message="Invalid or missing launch_token.",
    )

    if launch.is_expired:
        raise ValidationError("launch_token has expired.")

    if launch.app.oidc_client.client_id != client_id:
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

    id_token = generate_id_token(user=user, client=client, nonce=nonce)

    fragment = f"code={code}&id_token={id_token}"
    return f"{redirect_uri}#{fragment}", code, id_token


def create_app_launch(*, app: App, user: User) -> AppLaunch:
    if app.status != App.Status.ACTIVE:
        raise ValidationError("Cannot launch an app that is not active.")
    if not Installation.objects.filter(app=app, user=user, active=True).exists():
        raise ValidationError("User has not installed this app.")
    return AppLaunch.objects.create_launch(
        app=app, user=user, ttl_seconds=LAUNCH_TOKEN_TTL
    )


def build_launch_url(*, app_launch: AppLaunch) -> str:
    try:
        base = app_launch.app.url_config.launch_url
    except AppUrl.DoesNotExist:
        raise ValidationError("This app has no launch URL configured.")
    sep = "&" if "?" in base else "?"
    return (
        f"{base}{sep}"
        f"platform_user_id={app_launch.user.id}"
        f"&launch_token={app_launch.launch_token}"
    )


def create_payment(*, app: App, user: User) -> Payment:
    if app.is_free or app.amount is None:
        raise ValidationError("This app is free — no payment required.")
    return Payment.objects.create_payment(
        app=app, user=user, amount=app.amount, currency=app.currency
    )


def install_app(*, app: App, user: User, payment: Payment = None) -> Installation:
    if app.status != App.Status.ACTIVE:
        raise ValidationError("Only active apps can be installed.")

    if not app.is_free and payment is None:
        raise ValidationError("This app requires payment before installation.")

    existing = (
        Installation.objects.all_with_deleted().filter(app=app, user=user).first()
    )
    if existing:
        if existing.deleted:
            existing.deleted = None
            existing.active = True
            existing.save()
            return existing
        if existing.active:
            raise ValidationError("App is already installed.")
        existing.active = True
        existing.save(update_fields=["active"])
        return existing

    return Installation.objects.create_installation(app=app, user=user)


def uninstall_app(*, app: App, user: User) -> None:
    installation = Installation.objects.filter(app=app, user=user, active=True).first()
    if not installation:
        raise ValidationError("App is not installed.")
    installation.active = False
    installation.save(update_fields=["active"])


def create_or_update_review(
    *, app: App, user: User, rating: int, message: str = ""
) -> Review:
    existing = Review.objects.all_with_deleted().filter(app=app, user=user).first()
    if existing:
        existing.deleted = None
        existing.rating = rating
        existing.message = message
        existing.save()
        return existing

    if not Installation.objects.filter(app=app, user=user).exists():
        raise ValidationError("You can only review apps you have installed.")

    return Review.objects.create_review(
        app=app, user=user, rating=rating, message=message
    )


def delete_review(*, review: Review, user: User) -> None:
    if review.user_id != user.id:
        raise PermissionDenied("You can only delete your own reviews.")
    review.delete()


def create_moderator(*, user: User, is_chief: bool = False) -> ModeratorProfile:
    if hasattr(user, "moderator_profile"):
        raise ValidationError("This user is already a moderator.")
    return ModeratorProfile.objects.create_moderator(user=user, is_chief=is_chief)


def update_moderator(*, profile: ModeratorProfile, data: dict) -> ModeratorProfile:
    profile, _ = model_update(instance=profile, fields=["is_chief"], data=data)
    return profile
