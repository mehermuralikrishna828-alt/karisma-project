from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from accounts.utils import get_profile
from crowdfunding.models import Campaign
from philanthropy.models import PhilanthropyCause

from .forms import ITEM_FORMS, AmountForm, DonorDetailsForm, OtherDonationForm
from .models import Donation, DonationCategory, DonationDrive
from .services import (
    DonationError,
    ensure_default_categories,
    record_item_donation,
    record_money_donation,
)

FLOW_SESSION_KEY = "donation_flow"
STEPS = ["amount", "details", "review"]
QUICK_AMOUNTS = [100, 500, 1000, 2500, 5000]


def index(request):
    ensure_default_categories()
    today = timezone.localdate()
    categories = DonationCategory.objects.filter(is_active=True).annotate(
        total=Count("donations")
    )
    drives = (
        DonationDrive.objects.filter(is_active=True, end_date__gte=today, start_date__lte=today)
        .select_related("category")
        .order_by("end_date")
    )
    community = (
        Donation.objects.exclude(status=Donation.Status.CANCELLED)
        .select_related("category", "campaign", "cause", "drive")
        .order_by("-created_at")[:8]
    )
    my_recent = []
    if request.user.is_authenticated:
        my_recent = (
            Donation.objects.filter(user=request.user)
            .select_related("category", "campaign", "cause", "drive")
            .order_by("-created_at")[:5]
        )
    return render(
        request,
        "donations/index.html",
        {"categories": categories, "drives": drives, "community": community, "my_recent": my_recent},
    )


def category_detail(request, slug):
    ensure_default_categories()
    category = get_object_or_404(DonationCategory, slug=slug, is_active=True)
    if category.is_money:
        return redirect("donations:flow", kind="general", slug="general", step="amount")

    form_class = ITEM_FORMS.get(category.slug, OtherDonationForm)

    drive = None
    drive_id = request.GET.get("drive", "")
    if drive_id.isdigit():
        drive = DonationDrive.objects.filter(pk=drive_id, category=category, is_active=True).first()

    if request.method == "POST":
        if not request.user.is_authenticated:
            messages.info(request, "Please log in to submit your donation.")
            return redirect_to_login(request.get_full_path())
        form = form_class(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            try:
                donation = record_item_donation(
                    user=request.user,
                    category=category,
                    donor_name=data["donor_name"],
                    donor_email=data["donor_email"],
                    donor_phone=data["donor_phone"],
                    city=data["city"],
                    address=data.get("pickup_address", ""),
                    message=data.get("message", ""),
                    quantity=form.get_quantity(),
                    details=form.get_details(),
                    drive=drive,
                )
            except DonationError as exc:
                messages.error(request, str(exc))
            else:
                messages.success(request, "Thank you! Your donation has been recorded.")
                return redirect("donations:success", reference=donation.reference)
    else:
        initial = {}
        if request.user.is_authenticated:
            profile = get_profile(request.user)
            initial = {
                "donor_name": request.user.get_full_name(),
                "donor_email": request.user.email,
                "donor_phone": profile.phone,
                "city": profile.city,
            }
        form = form_class(initial=initial)

    drives = category.drives.filter(is_active=True, end_date__gte=timezone.localdate())[:3]
    recent = category.donations.exclude(status=Donation.Status.CANCELLED)[:5]
    return render(
        request,
        "donations/category_form.html",
        {"category": category, "form": form, "drive": drive, "drives": drives, "recent": recent},
    )


# ---------------------------------------------------------------------------
# Demo money donation flow:  amount -> details -> review -> confirm -> success
# ---------------------------------------------------------------------------
def _resolve_target(kind, slug):
    """Return (campaign, cause, title, subtitle, back_url) for the flow target."""
    if kind == "campaign":
        campaign = get_object_or_404(Campaign, slug=slug)
        if not campaign.is_accepting:
            raise DonationError("This campaign is no longer accepting donations.")
        return campaign, None, campaign.title, f"Campaign by {campaign.creator.get_full_name() or campaign.creator.username}", campaign.get_absolute_url()
    if kind == "cause":
        cause = get_object_or_404(PhilanthropyCause, slug=slug, is_active=True)
        return None, cause, cause.title, cause.get_category_display(), cause.get_absolute_url()
    if kind == "general" and slug == "general":
        return None, None, "Karisma General Fund", "Supports the platform's most urgent needs", reverse("donations:index")
    raise Http404("Unknown donation target.")


@login_required
def money_flow(request, kind, slug, step):
    if step not in STEPS:
        raise Http404("Unknown step.")
    try:
        campaign, cause, title, subtitle, back_url = _resolve_target(kind, slug)
    except DonationError as exc:
        messages.error(request, str(exc))
        return redirect("crowdfunding:list")

    flow_key = f"{kind}:{slug}"
    flow = request.session.get(FLOW_SESSION_KEY) or {}
    if flow.get("key") != flow_key:
        flow = {"key": flow_key}

    def flow_url(target_step):
        return reverse("donations:flow", kwargs={"kind": kind, "slug": slug, "step": target_step})

    context = {
        "step": step,
        "step_index": STEPS.index(step) + 1,
        "kind": kind,
        "target_slug": slug,
        "target_title": title,
        "target_subtitle": subtitle,
        "campaign": campaign,
        "cause": cause,
        "back_url": back_url,
        "quick_amounts": QUICK_AMOUNTS,
        "flow": flow,
    }

    if step == "amount":
        initial_amount = request.GET.get("amount") or flow.get("amount")
        form = AmountForm(request.POST or None, initial={"amount": initial_amount})
        if request.method == "POST" and form.is_valid():
            flow["amount"] = str(form.cleaned_data["amount"])
            request.session[FLOW_SESSION_KEY] = flow
            return redirect(flow_url("details"))
        context["form"] = form

    elif step == "details":
        if "amount" not in flow:
            return redirect(flow_url("amount"))
        initial = flow.get("donor") or {
            "donor_name": request.user.get_full_name(),
            "donor_email": request.user.email,
            "donor_phone": get_profile(request.user).phone,
        }
        form = DonorDetailsForm(request.POST or None, initial=initial)
        if request.method == "POST" and form.is_valid():
            flow["donor"] = {k: v for k, v in form.cleaned_data.items()}
            request.session[FLOW_SESSION_KEY] = flow
            return redirect(flow_url("review"))
        context["form"] = form

    else:  # review
        if "amount" not in flow:
            return redirect(flow_url("amount"))
        if "donor" not in flow:
            return redirect(flow_url("details"))
        donor = flow["donor"]
        if request.method == "POST":
            try:
                donation = record_money_donation(
                    user=request.user,
                    amount=flow["amount"],
                    donor_name=donor["donor_name"],
                    donor_email=donor["donor_email"],
                    donor_phone=donor.get("donor_phone", ""),
                    message=donor.get("message", ""),
                    is_anonymous=bool(donor.get("is_anonymous")),
                    payment_method=donor.get("payment_method", "upi"),
                    campaign=campaign,
                    cause=cause,
                )
            except DonationError as exc:
                messages.error(request, str(exc))
                return redirect(flow_url("amount"))
            request.session.pop(FLOW_SESSION_KEY, None)
            messages.success(request, "Donation successful! Thank you for your kindness (demo payment).")
            return redirect("donations:success", reference=donation.reference)
        context.update({"amount": flow["amount"], "donor": donor})

    return render(request, "donations/flow.html", context)


@login_required
def success(request, reference):
    donation = get_object_or_404(
        Donation.objects.select_related("category", "campaign", "cause", "drive"),
        reference=reference,
        user=request.user,
    )
    return render(request, "donations/success.html", {"donation": donation})
