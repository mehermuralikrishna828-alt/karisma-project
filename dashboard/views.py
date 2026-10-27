from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from accounts.forms import ProfileForm, UserForm
from accounts.models import Notification
from accounts.utils import get_profile
from crowdfunding.models import Campaign, SavedCampaign
from crowdfunding.services import check_deadline_notifications
from donations.models import Donation, DonationCategory
from philanthropy.models import PhilanthropyCause


def _month_sequence(count=6):
    today = timezone.localdate()
    year, month = today.year, today.month
    months = []
    for _ in range(count):
        months.append((year, month))
        month -= 1
        if month == 0:
            month, year = 12, year - 1
    months.reverse()
    return months


def build_chart_data(user):
    """Data for the three Chart.js charts on the dashboard overview."""
    donations = Donation.objects.filter(user=user).exclude(status=Donation.Status.CANCELLED)

    # 1) Money donated per month (last 6 months)
    months = _month_sequence(6)
    start = date(months[0][0], months[0][1], 1)
    rows = (
        donations.filter(category__slug="money", created_at__date__gte=start)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(total=Sum("amount"))
    )
    totals = {(r["month"].year, r["month"].month): float(r["total"]) for r in rows}
    timeline = {
        "labels": [date(y, m, 1).strftime("%b %Y") for y, m in months],
        "values": [totals.get((y, m), 0) for y, m in months],
    }

    # 2) Number of donations per category
    by_category = donations.values("category__name").annotate(n=Count("id")).order_by("-n")
    category = {
        "labels": [r["category__name"] for r in by_category],
        "values": [r["n"] for r in by_category],
    }

    # 3) Money distribution across campaigns / causes / general fund
    parts = {}
    for r in donations.filter(campaign__isnull=False).values("campaign__title").annotate(t=Sum("amount")):
        parts[r["campaign__title"]] = parts.get(r["campaign__title"], 0) + float(r["t"])
    for r in donations.filter(cause__isnull=False).values("cause__title").annotate(t=Sum("amount")):
        parts[r["cause__title"]] = parts.get(r["cause__title"], 0) + float(r["t"])
    general = donations.filter(
        category__slug="money", campaign__isnull=True, cause__isnull=True
    ).aggregate(t=Sum("amount"))["t"]
    if general:
        parts["General Fund"] = float(general)
    ordered = sorted(parts.items(), key=lambda kv: kv[1], reverse=True)
    top, rest = ordered[:6], ordered[6:]
    if rest:
        top.append(("Others", sum(v for _, v in rest)))
    distribution = {
        "labels": [(k[:30] + "…") if len(k) > 30 else k for k, _ in top],
        "values": [v for _, v in top],
    }
    return {"timeline": timeline, "category": category, "distribution": distribution}


@login_required
def home(request):
    user = request.user
    check_deadline_notifications(user=user)
    donations = Donation.objects.filter(user=user).select_related(
        "category", "campaign", "cause", "drive"
    )
    money = donations.filter(category__slug="money", status=Donation.Status.COMPLETED)
    stats = {
        "total_donated": money.aggregate(t=Sum("amount"))["t"] or 0,
        "campaigns_supported": money.filter(campaign__isnull=False).values("campaign").distinct().count(),
        "causes_supported": money.filter(cause__isnull=False).values("cause").distinct().count(),
        "items_donated": donations.exclude(category__slug="money")
        .exclude(status=Donation.Status.CANCELLED)
        .aggregate(t=Sum("quantity"))["t"]
        or 0,
        "donation_count": donations.exclude(status=Donation.Status.CANCELLED).count(),
    }
    context = {
        "profile": get_profile(user),
        "stats": stats,
        "recent_donations": donations[:6],
        "my_campaigns": Campaign.objects.filter(creator=user)[:3],
        "notifications": user.notifications.all()[:5],
        "chart_data": build_chart_data(user),
        "has_activity": stats["donation_count"] > 0,
    }
    return render(request, "dashboard/overview.html", context)


@login_required
def history(request):
    donations = (
        Donation.objects.filter(user=request.user)
        .select_related("category", "campaign", "cause", "drive")
        .order_by("-created_at")
    )
    category = request.GET.get("category", "")
    if category:
        donations = donations.filter(category__slug=category)
    page = Paginator(donations, 12).get_page(request.GET.get("page"))
    return render(
        request,
        "dashboard/history.html",
        {
            "page_obj": page,
            "donations": page.object_list,
            "categories": DonationCategory.objects.filter(is_active=True),
            "selected_category": category,
        },
    )


@login_required
def my_campaigns(request):
    campaigns = Campaign.objects.filter(creator=request.user).order_by("-created_at")
    return render(request, "dashboard/campaigns.html", {"campaigns": campaigns})


@login_required
def saved(request):
    saved_campaigns = (
        SavedCampaign.objects.filter(user=request.user)
        .select_related("campaign", "campaign__creator")
        .order_by("-created_at")
    )
    followed = PhilanthropyCause.objects.filter(followers=request.user, is_active=True)
    return render(
        request,
        "dashboard/saved.html",
        {
            "saved_campaigns": [item.campaign for item in saved_campaigns],
            "followed_causes": followed,
            "saved_campaign_ids": {item.campaign_id for item in saved_campaigns},
            "followed_cause_ids": set(followed.values_list("pk", flat=True)),
        },
    )


@login_required
def notifications(request):
    page = Paginator(request.user.notifications.all(), 15).get_page(request.GET.get("page"))
    return render(
        request,
        "dashboard/notifications.html",
        {"page_obj": page, "notifications": page.object_list},
    )


@login_required
@require_POST
def notifications_read_all(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    return redirect("dashboard:notifications")


@login_required
def notification_open(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read", "updated_at"])
    target = notification.link
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        return redirect(target)
    return redirect("dashboard:notifications")


@login_required
def settings_view(request):
    profile = get_profile(request.user)
    if request.method == "POST":
        user_form = UserForm(request.POST, instance=request.user, prefix="u")
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile, prefix="p")
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Your profile has been updated.")
            return redirect("dashboard:settings")
        messages.error(request, "Please correct the errors below.")
    else:
        user_form = UserForm(instance=request.user, prefix="u")
        profile_form = ProfileForm(instance=profile, prefix="p")
    return render(
        request,
        "dashboard/settings.html",
        {"user_form": user_form, "profile_form": profile_form},
    )
