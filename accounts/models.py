from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models

from core.models import TimeStampedModel

PHONE_VALIDATOR = RegexValidator(
    r"^(\+91[\-\s]?)?[6-9]\d{9}$", "Enter a valid 10-digit Indian mobile number."
)


class Profile(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    phone = models.CharField(max_length=15, blank=True, validators=[PHONE_VALIDATOR])
    city = models.CharField(max_length=80, blank=True)
    state = models.CharField(max_length=80, blank=True)
    bio = models.TextField(max_length=400, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True)

    class Meta:
        ordering = ["user__username"]

    def __str__(self):
        return f"Profile of {self.user.username}"

    @property
    def location(self):
        return ", ".join(part for part in (self.city, self.state) if part)


class Notification(TimeStampedModel):
    class Kind(models.TextChoices):
        DONATION = "donation", "Donation"
        CAMPAIGN = "campaign", "Campaign"
        UPDATE = "update", "Campaign update"
        DEADLINE = "deadline", "Deadline"
        SAVED = "saved", "Saved item"
        SYSTEM = "system", "System"

    ICONS = {
        "donation": "bi-heart-fill",
        "campaign": "bi-rocket-takeoff-fill",
        "update": "bi-megaphone-fill",
        "deadline": "bi-alarm-fill",
        "saved": "bi-bookmark-heart-fill",
        "system": "bi-stars",
    }

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.SYSTEM)
    title = models.CharField(max_length=140)
    message = models.TextField(max_length=500, blank=True)
    link = models.CharField(max_length=300, blank=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "is_read"])]

    def __str__(self):
        return f"{self.user.username}: {self.title}"

    @property
    def icon(self):
        return self.ICONS.get(self.kind, "bi-bell-fill")
