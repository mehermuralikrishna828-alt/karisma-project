"""Business logic for recording donations.

All donations, whether made via the UI or the seed command, go through these
functions so that campaign / cause totals stay consistent.
"""
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import F
from django.urls import reverse

from accounts.models import Notification
from accounts.utils import notify
from crowdfunding.models import Campaign
from philanthropy.models import PhilanthropyCause

from .constants import DEFAULT_CATEGORIES, MAX_DONATION, MIN_DONATION, MONEY_SLUG
from .models import Donation, DonationCategory, DonationDrive


class DonationError(Exception):
    """Raised when a donation cannot be accepted."""


def ensure_default_categories():
    """Create the eight standard donation categories if they don't exist yet."""
    if DonationCategory.objects.count() >= len(DEFAULT_CATEGORIES):
        return
    for item in DEFAULT_CATEGORIES:
        DonationCategory.objects.get_or_create(
            slug=item["slug"],
            defaults={
                "name": item["name"],
                "icon": item["icon"],
                "gradient": item["gradient"],
                "order": item["order"],
                "description": item["description"],
            },
        )


def get_money_category():
    ensure_default_categories()
    return DonationCategory.objects.get(slug=MONEY_SLUG)


def clean_amount(value):
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        raise DonationError("Please enter a valid amount.")
    if amount < MIN_DONATION:
        raise DonationError(f"The minimum donation is ₹{MIN_DONATION}.")
    if amount > MAX_DONATION:
        raise DonationError(f"A single donation cannot exceed ₹{MAX_DONATION:,}.")
    return amount


def _set_created_at(donation, created_at):
    if created_at is not None:
        Donation.objects.filter(pk=donation.pk).update(created_at=created_at)
        donation.created_at = created_at


@transaction.atomic
def record_money_donation(
    *,
    user,
    amount,
    donor_name,
    donor_email,
    donor_phone="",
    message="",
    is_anonymous=False,
    campaign=None,
    cause=None,
    payment_method="upi",
    created_at=None,
):
    """Record a (simulated) money donation and update the related totals."""
    amount = clean_amount(amount)
    if campaign is not None and cause is not None:
        raise DonationError("Choose either a campaign or a cause.")

    if campaign is not None:
        campaign = Campaign.objects.select_for_update().get(pk=campaign.pk)
        if not campaign.is_accepting:
            raise DonationError("This campaign is no longer accepting donations.")
    if cause is not None:
        cause = PhilanthropyCause.objects.select_for_update().get(pk=cause.pk)
        if not cause.is_active:
            raise DonationError("This cause is not accepting donations right now.")

    first_time = True
    if user is not None:
        previous = Donation.objects.filter(user=user, status=Donation.Status.COMPLETED)
        if campaign is not None:
            first_time = not previous.filter(campaign=campaign).exists()
        elif cause is not None:
            first_time = not previous.filter(cause=cause).exists()

    donation = Donation(
        user=user,
        category=get_money_category(),
        campaign=campaign,
        cause=cause,
        amount=amount,
        donor_name=donor_name,
        donor_email=donor_email,
        donor_phone=donor_phone,
        message=message,
        is_anonymous=is_anonymous,
        status=Donation.Status.COMPLETED,
        details={"payment_method": payment_method, "simulated": True},
    )
    donation.full_clean()
    donation.save()
    _set_created_at(donation, created_at)

    increment = 1 if first_time else 0
    if campaign is not None:
        Campaign.objects.filter(pk=campaign.pk).update(
            amount_raised=F("amount_raised") + amount,
            contributors_count=F("contributors_count") + increment,
        )
        campaign.refresh_from_db()
        if campaign.status == Campaign.Status.ACTIVE and campaign.amount_raised >= campaign.target_amount:
            campaign.status = Campaign.Status.FUNDED
            campaign.save(update_fields=["status", "updated_at"])
            notify(
                campaign.creator,
                Notification.Kind.CAMPAIGN,
                "Goal reached! 🎉",
                f"“{campaign.title}” is now fully funded.",
                campaign.get_absolute_url(),
            )
        if campaign.creator_id != getattr(user, "id", None):
            notify(
                campaign.creator,
                Notification.Kind.DONATION,
                "New supporter",
                f"{donation.public_name} contributed ₹{amount:,.0f} to “{campaign.title}”.",
                campaign.get_absolute_url(),
            )
    if cause is not None:
        PhilanthropyCause.objects.filter(pk=cause.pk).update(
            amount_raised=F("amount_raised") + amount,
            supporters_count=F("supporters_count") + increment,
        )

    target_title = donation.target_title
    notify(
        user,
        Notification.Kind.DONATION,
        "Donation successful",
        f"Thank you! Your demo donation of ₹{amount:,.0f} to {target_title} was recorded.",
        reverse("donations:success", kwargs={"reference": donation.reference}),
    )
    return donation


@transaction.atomic
def record_item_donation(
    *,
    user,
    category,
    donor_name,
    donor_email,
    donor_phone="",
    city="",
    address="",
    message="",
    quantity=1,
    details=None,
    drive=None,
    created_at=None,
    status=Donation.Status.PENDING,
):
    """Record an in-kind donation (food, clothes, blood registration, ...)."""
    if category.is_money:
        raise DonationError("Use the money donation flow for monetary contributions.")
    if quantity < 1:
        raise DonationError("Quantity must be at least 1.")

    donation = Donation(
        user=user,
        category=category,
        drive=drive,
        amount=Decimal("0.00"),
        quantity=quantity,
        donor_name=donor_name,
        donor_email=donor_email,
        donor_phone=donor_phone,
        city=city,
        address=address,
        message=message,
        status=status,
        details=details or {},
    )
    donation.full_clean()
    donation.save()
    _set_created_at(donation, created_at)

    if drive is not None:
        DonationDrive.objects.filter(pk=drive.pk).update(
            collected_quantity=F("collected_quantity") + quantity
        )

    verb = "registration as a blood donor" if category.slug == "blood" else "donation"
    notify(
        user,
        Notification.Kind.DONATION,
        f"{category.name} {verb} received",
        f"Thanks, {donor_name}! Our volunteers will contact you to arrange the next steps.",
        reverse("donations:success", kwargs={"reference": donation.reference}),
    )
    return donation
