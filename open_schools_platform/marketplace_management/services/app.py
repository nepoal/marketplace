import logging
import secrets
from typing import Tuple

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied

logger = logging.getLogger("marketplace_management")

from open_schools_platform.common.services import model_update
from open_schools_platform.marketplace_management.constants import (
    AUTH_CODE_TTL,
    LAUNCH_TOKEN_TTL,
)
from open_schools_platform.marketplace_management.models import (
    App,
    AppVersion,
    AppUrl,
    Category,
    Installation,
    Review,
    Payment,
    AppLaunch,
)
from open_schools_platform.user_management.users.models import User


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
    *, app: App, base_url: str, launch_path: str = "/"
) -> AppUrl:
    if hasattr(app, "url_config"):
        raise ValidationError("This app already has a URL configuration.")
    return AppUrl.objects.create_url(
        app=app,
        base_url=base_url,
        launch_path=launch_path,
    )


def update_app_url(*, app_url: AppUrl, data: dict) -> AppUrl:
    app_url, _ = model_update(
        instance=app_url,
        fields=["base_url", "launch_path"],
        data=data,
    )
    return app_url


def create_app_launch(*, app: App, user: User) -> AppLaunch:
    if app.status != App.Status.ACTIVE:
        raise ValidationError("Cannot launch an app that is not active.")
    if not Installation.objects.filter(app=app, user=user, active=True).exists():
        raise ValidationError("User has not installed this app.")
    launch = AppLaunch.objects.create_launch(
        app=app, user=user, ttl_seconds=LAUNCH_TOKEN_TTL
    )
    logger.info("App launched: user_id=%s app_id=%s", user.id, app.id)
    return launch


def build_launch_url(*, app_launch: AppLaunch) -> str:
    """Build the URL used to open an app in an iframe.

    Appends platform_user_id and launch_token as query parameters,
    using '?' or '&' depending on whether the base URL already has a query string.
    """
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
    if Payment.objects.filter(
        app=app, user=user, status=Payment.Status.COMPLETED
    ).exists():
        raise ValidationError("Payment for this app already exists.")
    payment = Payment(
        app=app,
        user=user,
        amount=app.amount,
        currency=app.currency,
        status=Payment.Status.COMPLETED,
    )
    payment.full_clean()
    payment.save()
    logger.info("Payment created: user_id=%s app_id=%s amount=%s %s", user.id, app.id, payment.amount, payment.currency)
    return payment


def install_app(*, app: App, user: User) -> Installation:
    """Install an app for the user.

    For paid apps a completed payment must exist first.
    Restores soft-deleted installations instead of creating new ones.
    """
    if app.status != App.Status.ACTIVE:
        raise ValidationError("Only active apps can be installed.")

    payment = None
    if not app.is_free:
        payment = Payment.objects.filter(
            app=app, user=user, status=Payment.Status.COMPLETED
        ).first()
        if payment is None:
            raise ValidationError("This app requires payment before installation.")

    with transaction.atomic():
        existing = (
            Installation.objects.all_with_deleted().filter(app=app, user=user).first()
        )
        if existing:
            if existing.deleted:
                existing.deleted = None
                existing.active = True
                existing.payment = payment
                existing.save()
                logger.info("App installed: user_id=%s app_id=%s", user.id, app.id)
                return existing
            if existing.active:
                raise ValidationError("App is already installed.")
            existing.active = True
            existing.payment = payment
            existing.save(update_fields=["active", "payment"])
            logger.info("App installed: user_id=%s app_id=%s", user.id, app.id)
            return existing

        installation = Installation.objects.create_installation(app=app, user=user, payment=payment)
        logger.info("App installed: user_id=%s app_id=%s", user.id, app.id)
        return installation


def uninstall_app(*, app: App, user: User) -> None:
    installation = Installation.objects.filter(app=app, user=user, active=True).first()
    if not installation:
        raise ValidationError("App is not installed.")
    installation.active = False
    installation.save(update_fields=["active"])
    logger.info("App uninstalled: user_id=%s app_id=%s", user.id, app.id)


def create_or_update_review(
    *, app: App, user: User, rating: int, message: str = ""
) -> Review:
    """Create or update a review, restoring soft-deleted ones if they exist.

    New reviews require the user to have the app installed.
    Updating an existing review does not require an active installation.
    """
    existing = Review.objects.all_with_deleted().filter(app=app, user=user).first()
    if existing:
        existing.deleted = None
        existing.rating = rating
        existing.message = message
        existing.save()
        logger.info("Review updated: user_id=%s app_id=%s rating=%s", user.id, app.id, rating)
        return existing

    if not Installation.objects.filter(app=app, user=user).exists():
        raise ValidationError("You can only review apps you have installed.")

    review = Review.objects.create_review(app=app, user=user, rating=rating, message=message)
    logger.info("Review created: user_id=%s app_id=%s rating=%s", user.id, app.id, rating)
    return review


def delete_review(*, review: Review, user: User) -> None:
    if review.user_id != user.id:
        raise PermissionDenied("You can only delete your own reviews.")
    review.delete()
    logger.info("Review deleted: user_id=%s app_id=%s", review.user_id, review.app_id)
