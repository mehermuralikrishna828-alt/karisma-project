from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from accounts.models import Notification
from accounts.utils import notify

from .models import Campaign


def campaign_audience(campaign):
    """User ids of everyone who donated to or saved a campaign (excluding the creator)."""
    donors = campaign.donations.exclude(status="cancelled").values_list("user_id", flat=True)
    savers = campaign.saves.values_list("user_id", flat=True)
    return (set(donors) | set(savers)) - {None, campaign.creator_id}


def notify_campaign_update(update):
    """Tell supporters and people who saved the campaign about a new update."""
    from django.contrib.auth import get_user_model

    campaign = update.campaign
    link = campaign.get_absolute_url() + "#updates"
    savers = set(campaign.saves.values_list("user_id", flat=True))
    users = get_user_model().objects.filter(pk__in=campaign_audience(campaign))
    for user in users:
        kind = Notification.Kind.SAVED if user.pk in savers else Notification.Kind.UPDATE
        notify(user, kind, f"New update: {campaign.title}", update.title, link)


def check_deadline_notifications(user=None, days=3):
    """Create one 'deadline approaching' notification per campaign/user pair.

    Notifies the creator, donors and savers of active campaigns that end within
    ``days`` days. When ``user`` is given only that user is considered.
    Returns the number of notifications created.
    """
    today = timezone.localdate()
    campaigns = Campaign.objects.filter(
        status=Campaign.Status.ACTIVE,
        deadline__gte=today,
        deadline__lte=today + timedelta(days=days),
    ).select_related("creator")

    created = 0
    for campaign in campaigns:
        audience = campaign_audience(campaign) | {campaign.creator_id}
        if user is not None:
            audience &= {user.pk}
        link = reverse("crowdfunding:detail", kwargs={"slug": campaign.slug})
        remaining = campaign.days_left
        when = "today" if remaining == 0 else f"in {remaining} day{'s' if remaining != 1 else ''}"
        from django.contrib.auth import get_user_model

        for member in get_user_model().objects.filter(pk__in=audience):
            already = Notification.objects.filter(
                user=member, kind=Notification.Kind.DEADLINE, link=link
            ).exists()
            if not already:
                notify(
                    member,
                    Notification.Kind.DEADLINE,
                    f"Deadline approaching: {campaign.title}",
                    f"This campaign ends {when}.",
                    link,
                )
                created += 1
    return created
