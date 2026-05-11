from decimal import Decimal
from typing import List, Tuple

from open_schools_platform.marketplace_management.models import (
    App,
    AppLaunch,
    AppVersion,
    Category,
    Installation,
    Payment,
    Review,
)
from open_schools_platform.marketplace_management.models.app import AppUrl
from open_schools_platform.marketplace_management.models.moderator import ModeratorProfile
from open_schools_platform.marketplace_management.models.oidc import OidcClient
from open_schools_platform.user_management.users.models import User
from open_schools_platform.marketplace_management.services.app import (
    create_app,
    create_app_url,
    create_category,
)
from open_schools_platform.marketplace_management.services.oidc import create_oidc_client_for_app
from open_schools_platform.user_management.users.models import User


def create_test_category(name: str = "Test Category") -> Category:
    return create_category(name=name)


def create_test_app(
    name: str = "Test App",
    status: str = App.Status.ACTIVE,
    is_free: bool = True,
    amount=None,
    currency: str = "RUB",
    with_url: bool = False,
    with_oidc: bool = False,
    redirect_uris: List[str] = None,
) -> App:
    app = create_app(
        name=name,
        short_description="A test application",
        is_free=is_free,
        amount=amount,
        currency=currency,
    )
    if app.status != status:
        app.status = status
        app.save(update_fields=["status"])
    if with_url:
        create_app_url(
            app=app,
            base_url="https://testapp.example.com",
            launch_path="/launch",
        )
    if with_oidc or redirect_uris:
        uris = redirect_uris or ["https://testapp.example.com/oidc/callback"]
        create_oidc_client_for_app(app=app, redirect_uris=uris)
    return app


def create_test_paid_app(
    name: str = "Test Paid App",
    amount: Decimal = Decimal("99.99"),
    currency: str = "RUB",
    status: str = App.Status.ACTIVE,
    with_url: bool = False,
    with_oidc: bool = False,
    redirect_uris: List[str] = None,
) -> App:
    return create_test_app(
        name=name,
        status=status,
        is_free=False,
        amount=amount,
        currency=currency,
        with_url=with_url,
        with_oidc=with_oidc,
        redirect_uris=redirect_uris,
    )


def create_test_installation(app: App, user: User, payment: Payment = None) -> Installation:
    return Installation.objects.create_installation(app=app, user=user, payment=payment)


def create_test_payment(
    app: App,
    user: User,
    status: str = Payment.Status.COMPLETED,
) -> Payment:
    payment = Payment.objects.create_payment(
        app=app,
        user=user,
        amount=app.amount or Decimal("99.99"),
        currency=app.currency,
    )
    if payment.status != status:
        payment.status = status
        payment.save(update_fields=["status"])
    return payment


def create_test_review(app: App, user: User, rating: int = 5, message: str = "") -> Review:
    return Review.objects.create_review(app=app, user=user, rating=rating, message=message)


def create_test_app_launch(app: App, user: User) -> AppLaunch:
    return AppLaunch.objects.create_launch(app=app, user=user)


def create_test_oidc_client(
    app: App, redirect_uris: List[str] = None
) -> OidcClient:
    uris = redirect_uris or ["https://testapp.example.com/oidc/callback"]
    client, _ = OidcClient.objects.create_client(app=app, redirect_uris=uris)
    return client


def create_test_oidc_client_with_secret(
    app: App, redirect_uris: List[str] = None
) -> Tuple[OidcClient, str]:
    uris = redirect_uris or ["https://testapp.example.com/oidc/callback"]
    return OidcClient.objects.create_client(app=app, redirect_uris=uris)


def create_test_app_version(app: App, version: str = "1.0.0") -> AppVersion:
    return AppVersion.objects.create_version(app=app, version=version)


def create_test_app_url(
    app: App,
    base_url: str = "https://testapp.example.com",
    launch_path: str = "/launch",
) -> AppUrl:
    return AppUrl.objects.create_url(app=app, base_url=base_url, launch_path=launch_path)


def create_test_moderator(user: User, is_chief: bool = False) -> ModeratorProfile:
    return ModeratorProfile.objects.create_moderator(user=user, is_chief=is_chief)
