import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from core.models import TimeStampedModel
from crowdfunding.models import Campaign
from philanthropy.models import PhilanthropyCause

from .constants import MAX_DONATION, MIN_DONATION, MONEY_SLUG


def generate_reference():
    return "KRS-" + uuid.uuid4().hex[:10].upper()


class DonationCategory(models.Model):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=60, unique=True)
    icon = models.CharField(max_length=40, default="bi-gift", help_text="Bootstrap Icons class")
    gradient = models.CharField(max_length=30, default="grad-teal")
    description = models.CharField(max_length=220, blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "donation category"
        verbose_name_plural = "donation categories"

    def __str__(self):
        return self.name

    @property
    def is_money(self):
        return self.slug == MONEY_SLUG


class DonationDrive(TimeStampedModel):
    category = models.ForeignKey(DonationCategory, on_delete=models.CASCADE, related_name="drives")
    title = models.CharField(max_length=140)
    description = models.TextField()
    location = models.CharField(max_length=140)
    organizer = models.CharField(max_length=120, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    unit = models.CharField(max_length=20, default="items")
    goal_quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    collected_quantity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["end_date"]

    def __str__(self):
        return self.title

    def clean(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": "The end date cannot be before the start date."})

    @property
    def is_open(self):
        today = timezone.localdate()
        return self.is_active and self.start_date <= today <= self.end_date

    @property
    def progress_percent(self):
        if not self.goal_quantity:
            return 0
        return min(int(self.collected_quantity * 100 / self.goal_quantity), 100)

    @property
    def days_left(self):
        return max((self.end_date - timezone.localdate()).days, 0)


class Donation(TimeStampedModel):
    class Status(models.TextChoices):
        COMPLETED = "completed", "Completed"
        PENDING = "pending", "Scheduled / pending pickup"
        CANCELLED = "cancelled", "Cancelled"

    reference = models.CharField(max_length=20, unique=True, default=generate_reference, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="donations",
    )
    category = models.ForeignKey(DonationCategory, on_delete=models.PROTECT, related_name="donations")
    campaign = models.ForeignKey(
        Campaign, on_delete=models.PROTECT, null=True, blank=True, related_name="donations"
    )
    cause = models.ForeignKey(
        PhilanthropyCause, on_delete=models.PROTECT, null=True, blank=True, related_name="donations"
    )
    drive = models.ForeignKey(
        DonationDrive, on_delete=models.SET_NULL, null=True, blank=True, related_name="donations"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    quantity = models.PositiveIntegerField(default=0, help_text="Number of items / units (non-money)")
    donor_name = models.CharField(max_length=100)
    donor_email = models.EmailField()
    donor_phone = models.CharField(max_length=20, blank=True)
    city = models.CharField(max_length=80, blank=True)
    address = models.TextField(blank=True)
    message = models.CharField(max_length=300, blank=True)
    is_anonymous = models.BooleanField(default=False)
    details = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.COMPLETED)
    is_demo = models.BooleanField(default=True, editable=False, help_text="Payments are simulated.")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.reference} · {self.donor_name} · {self.category}"

    def clean(self):
        errors = {}
        if self.amount is not None and self.amount < 0:
            errors["amount"] = "A donation amount cannot be negative."
        if self.campaign_id and self.cause_id:
            errors["cause"] = "A donation can support either a campaign or a cause, not both."
        is_money = self.category_id and self.category.is_money
        if is_money:
            if self.amount is None or self.amount < MIN_DONATION:
                errors["amount"] = f"Money donations must be at least ₹{MIN_DONATION}."
            elif self.amount > MAX_DONATION:
                errors["amount"] = f"A single donation cannot exceed ₹{MAX_DONATION:,}."
        elif self.category_id:
            if self.campaign_id or self.cause_id:
                errors["category"] = "Only money donations can be linked to campaigns or causes."
            if self.amount and self.amount > 0:
                errors["amount"] = "Item donations cannot carry a money amount."
        if errors:
            raise ValidationError(errors)

    # ---- helpers ----------------------------------------------------------
    @property
    def is_money(self):
        return self.category.is_money

    @property
    def target(self):
        return self.campaign or self.cause

    @property
    def target_title(self):
        target = self.target
        if target:
            return target.title
        return "Karisma General Fund" if self.is_money else (self.drive.title if self.drive else "Direct donation")

    @property
    def public_name(self):
        return "Anonymous" if self.is_anonymous else self.donor_name

    @property
    def details_items(self):
        """Readable (label, value) pairs of category-specific details."""
        rows = []
        for key, value in (self.details or {}).items():
            if key in {"simulated"} or value in ("", None, False):
                continue
            label = key.replace("_", " ").capitalize()
            rows.append((label, "Yes" if value is True else value))
        return rows
