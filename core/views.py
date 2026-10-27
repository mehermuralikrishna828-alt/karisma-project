from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone

from crowdfunding.models import Campaign
from crowdfunding.utils import get_saved_campaign_ids
from donations.models import Donation, DonationCategory
from donations.services import ensure_default_categories
from philanthropy.models import PhilanthropyCause
from philanthropy.utils import get_followed_cause_ids


def home(request):
    ensure_default_categories()
    today = timezone.localdate()
    open_campaigns = Campaign.objects.filter(
        status=Campaign.Status.ACTIVE, deadline__gte=today
    ).select_related("creator", "creator__profile")

    featured_campaigns = list(
        open_campaigns.filter(is_featured=True).order_by("-amount_raised")[:3]
    )
    if len(featured_campaigns) < 3:
        extra = open_campaigns.exclude(pk__in=[c.pk for c in featured_campaigns]).order_by(
            "-contributors_count"
        )[: 3 - len(featured_campaigns)]
        featured_campaigns += list(extra)

    recent_campaigns = open_campaigns.order_by("-created_at")[:6]
    featured_causes = PhilanthropyCause.objects.filter(is_active=True, is_featured=True)[:3]
    if not featured_causes:
        featured_causes = PhilanthropyCause.objects.filter(is_active=True)[:3]

    valid = Donation.objects.exclude(status=Donation.Status.CANCELLED)
    money = valid.filter(category__slug="money", status=Donation.Status.COMPLETED)
    stats = {
        "total_raised": money.aggregate(total=Sum("amount"))["total"] or 0,
        "campaigns": Campaign.objects.exclude(status=Campaign.Status.CANCELLED).count(),
        "donors": valid.exclude(user__isnull=True).values("user").distinct().count(),
        "items": valid.exclude(category__slug="money").aggregate(total=Sum("quantity"))["total"] or 0,
    }

    context = {
        "featured_campaigns": featured_campaigns,
        "recent_campaigns": recent_campaigns,
        "featured_causes": featured_causes,
        "categories": DonationCategory.objects.filter(is_active=True),
        "stats": stats,
        "saved_campaign_ids": get_saved_campaign_ids(request.user),
        "followed_cause_ids": get_followed_cause_ids(request.user),
        "campaign_categories": Campaign.Category.choices,
    }
    return render(request, "core/home.html", context)
