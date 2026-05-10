import secrets
import uuid

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


class InstallationManager(BaseManager):
    def create_installation(self, app, user, payment=None, expires_at=None):
        installation = self.model(
            app=app, user=user, active=True, payment=payment, expires_at=expires_at
        )
        installation.full_clean()
        installation.save(using=self._db)
        return installation


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
