import secrets
import uuid

import safedelete
from django.contrib.auth.hashers import make_password, check_password
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Avg
from django.utils import timezone

from open_schools_platform.common.models import BaseModel, BaseManager
from open_schools_platform.user_management.users.models import User


class CategoryManager(BaseManager):
    def create_category(self, name: str):
        category = self.model(name=name)
        category.full_clean()
        category.save(using=self._db)
        return category


class Category(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=200, unique=True)

    objects = CategoryManager()

    class Meta:
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class AppManager(BaseManager):
    def create_app(self, **kwargs):
        app = self.model(**kwargs)
        app.full_clean()
        app.save(using=self._db)
        return app


class App(BaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        REJECTED = "rejected", "Rejected"
        SUSPENDED = "suspended", "Suspended"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=200)
    short_description = models.CharField(max_length=500, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    icon_url = models.URLField(blank=True)
    screenshots = models.JSONField(default=list, blank=True)
    categories = models.ManyToManyField(Category, blank=True, related_name="apps")
    is_free = models.BooleanField(default=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=10, default="RUB", blank=True)

    objects = AppManager()

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.is_free:
            self.amount = None
        else:
            errors = {}
            if self.amount is None:
                errors["amount"] = "Укажите цену для платного приложения."
            if not self.currency:
                errors["currency"] = "Укажите валюту для платного приложения."
            if errors:
                raise ValidationError(errors)

    def __str__(self):
        return self.name

    @property
    def average_rating(self):
        result = self.reviews.aggregate(Avg("rating"))["rating__avg"]
        return round(result, 2) if result is not None else None

    @property
    def reviews_count(self):
        return self.reviews.count()


class AppVersionManager(BaseManager):
    def create_version(self, **kwargs):
        version = self.model(**kwargs)
        version.full_clean()
        version.save(using=self._db)
        return version


class AppVersion(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name="versions")
    version = models.CharField(max_length=50)
    description = models.CharField(max_length=500, blank=True)
    date = models.DateTimeField(default=timezone.now)

    objects = AppVersionManager()

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.app.name} v{self.version}"


class AppUrlManager(BaseManager):
    def create_url(self, **kwargs):
        url = self.model(**kwargs)
        url.full_clean()
        url.save(using=self._db)
        return url


class AppUrl(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    app = models.OneToOneField(App, on_delete=models.CASCADE, related_name="url_config")
    base_url = models.URLField()
    launch_path = models.CharField(max_length=500, default="/")

    objects = AppUrlManager()

    def __str__(self):
        return f"{self.app.name}: {self.base_url}"

    @property
    def launch_url(self):
        return f"{self.base_url.rstrip('/')}/{self.launch_path.lstrip('/')}"


class OidcClientManager(BaseManager):
    def create_client(self, app, redirect_uris: list):
        client_id = f"marketplace-{secrets.token_urlsafe(24)}"
        client_secret = secrets.token_urlsafe(48)
        client = self.model(
            app=app,
            client_id=client_id,
            client_secret_hash=make_password(client_secret),
            redirect_uris=redirect_uris,
        )
        client.full_clean()
        client.save(using=self._db)
        return client, client_secret


class OidcClient(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    app = models.OneToOneField(
        App, on_delete=models.CASCADE, related_name="oidc_client"
    )
    client_id = models.CharField(max_length=128, unique=True)
    client_secret_hash = models.CharField(max_length=256)
    redirect_uris = models.JSONField(default=list, blank=True)

    objects = OidcClientManager()

    def verify_secret(self, secret: str) -> bool:
        return check_password(secret, self.client_secret_hash)

    def get_client_id(self) -> str:
        return self.client_id

    def get_default_redirect_uri(self) -> str:
        return self.redirect_uris[0] if self.redirect_uris else ""

    def get_allowed_scope(self, scope: str) -> str:
        allowed = {"openid"}
        return " ".join(s for s in scope.split() if s in allowed)

    def check_redirect_uri(self, redirect_uri: str) -> bool:
        return redirect_uri in self.redirect_uris

    def check_client_secret(self, client_secret: str) -> bool:
        return self.verify_secret(client_secret)

    def check_endpoint_auth_method(self, method: str, endpoint: str) -> bool:
        return method in ("client_secret_basic", "client_secret_post")

    def check_grant_type(self, grant_type: str) -> bool:
        return grant_type in ("authorization_code", "refresh_token")

    def check_response_type(self, response_type: str) -> bool:
        return all(rt in {"code", "id_token"} for rt in response_type.split())

    def __str__(self):
        return f"OidcClient({self.client_id[:20]}...)"


class OidcAuthorizationCode(BaseModel):
    _safedelete_policy = safedelete.config.HARD_DELETE

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    code = models.CharField(max_length=256, unique=True)
    client = models.ForeignKey(
        OidcClient, on_delete=models.CASCADE, related_name="auth_codes"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="oidc_auth_codes"
    )
    redirect_uri = models.CharField(max_length=500)
    nonce = models.CharField(max_length=256, blank=True)
    scope = models.CharField(max_length=200, default="openid")
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    objects = BaseManager()

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    def get_redirect_uri(self) -> str:
        return self.redirect_uri

    def get_scope(self) -> str:
        return self.scope

    def get_auth_time(self) -> int:
        return int(self.created_at.timestamp())

    def get_nonce(self) -> str:
        return self.nonce

    def __str__(self):
        return f"AuthCode({self.code[:16]}...)"


class OidcAccessToken(BaseModel):
    _safedelete_policy = safedelete.config.HARD_DELETE

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    token = models.CharField(max_length=256, unique=True)
    client = models.ForeignKey(
        OidcClient, on_delete=models.CASCADE, related_name="access_tokens"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="oidc_access_tokens"
    )
    scope = models.CharField(max_length=200, default="openid")
    expires_at = models.DateTimeField()

    objects = BaseManager()

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def expires_in(self):
        delta = self.expires_at - timezone.now()
        return max(0, int(delta.total_seconds()))

    def get_client_id(self) -> str:
        return self.client.client_id

    def get_scope(self) -> str:
        return self.scope

    def get_expires_in(self) -> int:
        return max(0, int((self.expires_at - timezone.now()).total_seconds()))

    def get_expires_at(self) -> int:
        return int(self.expires_at.timestamp())

    def is_revoked(self) -> bool:
        return False

    def __str__(self):
        return f"AccessToken({self.token[:16]}...)"


class OidcRefreshToken(BaseModel):
    _safedelete_policy = safedelete.config.HARD_DELETE

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    token = models.CharField(max_length=256, unique=True)
    client = models.ForeignKey(
        OidcClient, on_delete=models.CASCADE, related_name="refresh_tokens"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="oidc_refresh_tokens"
    )
    access_token = models.OneToOneField(
        OidcAccessToken,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="refresh_token",
    )
    expires_at = models.DateTimeField()

    objects = BaseManager()

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    def get_scope(self) -> str:
        return self.access_token.scope if self.access_token else "openid"

    def get_client_id(self) -> str:
        return self.client.client_id

    def check_client(self, client) -> bool:
        return self.client_id == client.pk

    def __str__(self):
        return f"RefreshToken({self.token[:16]}...)"


class AppLaunchManager(BaseManager):
    def create_launch(self, app, user, ttl_seconds: int = 300):
        launch_token = secrets.token_urlsafe(48)
        expires_at = timezone.now() + timezone.timedelta(seconds=ttl_seconds)
        launch = self.model(
            app=app, user=user, launch_token=launch_token, token_exp=expires_at
        )
        launch.full_clean()
        launch.save(using=self._db)
        return launch


class AppLaunch(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name="launches")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="app_launches"
    )
    launch_token = models.CharField(max_length=256, unique=True)
    token_exp = models.DateTimeField()

    objects = AppLaunchManager()

    @property
    def is_expired(self):
        return timezone.now() > self.token_exp

    def __str__(self):
        return f"Launch({self.app.name}, {self.user})"


class InstallationManager(BaseManager):
    def create_installation(self, app, user, payment=None, expires_at=None):
        installation = self.model(
            app=app, user=user, active=True, payment=payment, expires_at=expires_at
        )
        installation.full_clean()
        installation.save(using=self._db)
        return installation


class PaymentManager(BaseManager):
    def create_payment(self, app, user, amount, currency: str = "RUB"):
        payment = self.model(app=app, user=user, amount=amount, currency=currency)
        payment.full_clean()
        payment.save(using=self._db)
        return payment


class Payment(BaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name="payments")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="marketplace_payments"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="RUB")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )

    objects = PaymentManager()

    def __str__(self):
        return f"Payment({self.user}, {self.app.name}, {self.amount} {self.currency}, {self.status})"


class Installation(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name="installations")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="marketplace_installations"
    )
    active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="installations",
    )

    objects = InstallationManager()

    def __str__(self):
        return f"{self.user} → {self.app.name}"


class ReviewManager(BaseManager):
    def create_review(self, app, user, rating: int, message: str = ""):
        review = self.model(app=app, user=user, rating=rating, message=message)
        review.full_clean()
        review.save(using=self._db)
        return review


class Review(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="marketplace_reviews"
    )
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    message = models.TextField(blank=True)

    objects = ReviewManager()

    def __str__(self):
        return f"{self.user} → {self.app.name}: {self.rating}/5"


class ModeratorProfileManager(BaseManager):
    def create_moderator(self, user, is_chief: bool = False):
        profile = self.model(user=user, is_chief=is_chief)
        profile.full_clean()
        profile.save(using=self._db)
        return profile


class ModeratorProfile(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="moderator_profile"
    )
    is_chief = models.BooleanField(default=False)

    objects = ModeratorProfileManager()

    def __str__(self):
        role = "Chief Moderator" if self.is_chief else "Moderator"
        return f"{role}: {self.user}"
