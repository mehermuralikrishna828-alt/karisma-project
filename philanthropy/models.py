from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from core.models import TimeStampedModel


class PhilanthropyCause(TimeStampedModel):
    class Category(models.TextChoices):
        WATER = "water", "Clean Water"
        TREES = "trees", "Tree Plantation"
        EDUCATION = "education", "Education"
        HUNGER = "hunger", "Hunger Relief"
        HOUSING = "housing", "Housing"
        CLIMATE = "climate", "Climate Action"
        ANIMALS = "animals", "Animal Welfare"
        HEALTH = "health", "Healthcare"

    CATEGORY_STYLE = {
        "water": ("bi-droplet-half", "grad-sky"),
        "trees": ("bi-tree", "grad-emerald"),
        "education": ("bi-mortarboard", "grad-indigo"),
        "hunger": ("bi-cup-hot", "grad-orange"),
        "housing": ("bi-house-heart", "grad-amber"),
        "climate": ("bi-wind", "grad-teal"),
        "animals": ("bi-suit-heart", "grad-rose"),
        "health": ("bi-heart-pulse", "grad-crimson"),
    }

    title = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, editable=False)
    category = models.CharField(max_length=20, choices=Category.choices)
    description = models.TextField()
    beneficiary_info = models.TextField(blank=True, help_text="Who benefits from this cause?")
    target_amount = models.DecimalField(
        max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("1000"))]
    )
    amount_raised = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00"), editable=False
    )
    supporters_count = models.PositiveIntegerField(default=0, editable=False)
    cover_image = models.ImageField(upload_to="causes/", blank=True)
    impact_stats = models.JSONField(
        default=list,
        blank=True,
        help_text='List of objects, e.g. [{"value": "12,500", "label": "litres delivered daily"}]',
    )
    impact_note = models.CharField(
        max_length=200, blank=True, help_text="e.g. ₹500 plants and protects 10 saplings"
    )
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    followers = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="followed_causes", blank=True
    )

    class Meta:
        ordering = ["title"]
        verbose_name = "philanthropy cause"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:100] or "cause"
            slug, counter = base, 2
            while PhilanthropyCause.objects.filter(slug=slug).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("philanthropy:detail", kwargs={"slug": self.slug})

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
    def stats_list(self):
        """Impact stats that are well-formed, for safe template rendering."""
        if not isinstance(self.impact_stats, list):
            return []
        return [s for s in self.impact_stats if isinstance(s, dict) and "value" in s and "label" in s]
