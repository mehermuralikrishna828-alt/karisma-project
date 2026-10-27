from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from core.models import TimeStampedModel


class Campaign(TimeStampedModel):
    class Category(models.TextChoices):
        MEDICAL = "medical", "Medical"
        EDUCATION = "education", "Education"
        ENVIRONMENT = "environment", "Environment"
        COMMUNITY = "community", "Community"
        ANIMAL = "animal", "Animal Welfare"
        DISASTER = "disaster", "Disaster Relief"
        WOMEN = "women", "Women Empowerment"
        ARTS = "arts", "Arts & Culture"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        FUNDED = "funded", "Fully funded"
        CLOSED = "closed", "Closed"
        CANCELLED = "cancelled", "Cancelled"

    CATEGORY_STYLE = {
        "medical": ("bi-heart-pulse", "grad-crimson"),
        "education": ("bi-mortarboard", "grad-indigo"),
        "environment": ("bi-tree", "grad-emerald"),
        "community": ("bi-people", "grad-teal"),
        "animal": ("bi-suit-heart", "grad-amber"),
        "disaster": ("bi-cloud-lightning-rain", "grad-sky"),
        "women": ("bi-gender-female", "grad-rose"),
        "arts": ("bi-music-note-beamed", "grad-violet"),
    }

    MIN_TARGET = Decimal("1000")
    MAX_TARGET = Decimal("100000000")
    MAX_DURATION_DAYS = 365

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="campaigns"
    )
    title = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, editable=False)
    short_description = models.CharField(max_length=200)
    description = models.TextField()
    impact_info = models.TextField("Impact information", blank=True)
    beneficiary = models.CharField(max_length=150, blank=True)
    location = models.CharField(max_length=120)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.COMMUNITY)
    target_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(MIN_TARGET), MaxValueValidator(MAX_TARGET)],
        help_text="Funding goal in ₹ (minimum ₹1,000).",
    )
    amount_raised = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00"), editable=False
    )
    contributors_count = models.PositiveIntegerField(default=0, editable=False)
    deadline = models.DateField()
    image = models.ImageField(upload_to="campaigns/", blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    is_verified = models.BooleanField(default=False, help_text="Verified by the Karisma team.")
    is_featured = models.BooleanField(default=False)
    saved_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="SavedCampaign",
        related_name="saved_campaigns",
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "deadline"]),
            models.Index(fields=["category"]),
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._orig_deadline = self.deadline
        self._orig_status = self.status

    def __str__(self):
        return self.title

    # ---- validation -------------------------------------------------------
    def clean(self):
        errors = {}
        today = timezone.localdate()
        deadline_changed = self.pk is None or self.deadline != self._orig_deadline

        if self.deadline and deadline_changed:
            if self.deadline <= today:
                errors["deadline"] = "The deadline must be a future date."
            elif self.deadline > today + timedelta(days=self.MAX_DURATION_DAYS):
                errors["deadline"] = "Campaigns can run for at most one year."

        if self.pk and self.target_amount is not None and self.target_amount < self.amount_raised:
            errors["target_amount"] = "The target cannot be lower than the amount already raised."

        if self.pk:
            if self._orig_status == self.Status.CANCELLED and self.status != self.Status.CANCELLED:
                errors.setdefault(NON_FIELD_ERRORS, []).append(
                    "A cancelled campaign cannot be re-opened."
                )
            if (
                self._orig_status == self.Status.FUNDED
                and self.status == self.Status.ACTIVE
                and self.target_amount is not None
                and self.amount_raised >= self.target_amount
            ):
                errors["target_amount"] = "Increase the target before re-opening a fully funded campaign."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._generate_slug()
        super().save(*args, **kwargs)
        self._orig_deadline = self.deadline
        self._orig_status = self.status

    def _generate_slug(self):
        base = slugify(self.title)[:100] or "campaign"
        slug, counter = base, 2
        while Campaign.objects.filter(slug=slug).exists():
            slug = f"{base}-{counter}"
            counter += 1
        return slug

    # ---- presentation helpers --------------------------------------------
    def get_absolute_url(self):
        return reverse("crowdfunding:detail", kwargs={"slug": self.slug})

    @property
    def icon(self):
        return self.CATEGORY_STYLE.get(self.category, ("bi-heart", "grad-teal"))[0]

    @property
    def gradient(self):
        return self.CATEGORY_STYLE.get(self.category, ("bi-heart", "grad-teal"))[1]

    @property
    def raw_percent(self):
        if not self.target_amount:
            return 0
        return int(self.amount_raised * 100 / self.target_amount)

    @property
    def progress_percent(self):
        return min(self.raw_percent, 100)

    @property
    def amount_remaining(self):
        return max(self.target_amount - self.amount_raised, Decimal("0"))

    @property
    def days_left(self):
        return max((self.deadline - timezone.localdate()).days, 0)

    @property
    def is_expired(self):
        return self.deadline < timezone.localdate()

    @property
    def is_accepting(self):
        return self.status == self.Status.ACTIVE and not self.is_expired

    @property
    def is_ending_soon(self):
        return self.is_accepting and self.days_left <= 7

    @property
    def status_label(self):
        if self.status == self.Status.ACTIVE and self.is_expired:
            return "Ended"
        return self.get_status_display()

    @property
    def status_badge(self):
        if self.status == self.Status.FUNDED:
            return "success"
        if self.status == self.Status.CANCELLED:
            return "danger"
        if self.status == self.Status.CLOSED or self.is_expired:
            return "secondary"
        return "primary"


class CampaignUpdate(TimeStampedModel):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="updates")
    title = models.CharField(max_length=140)
    body = models.TextField()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.campaign.title}: {self.title}"


class SavedCampaign(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_campaign_items"
    )
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="saves")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "campaign"], name="unique_saved_campaign")
        ]

    def __str__(self):
        return f"{self.user} saved {self.campaign}"
