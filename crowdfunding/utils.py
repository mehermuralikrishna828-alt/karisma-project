from .models import SavedCampaign


def get_saved_campaign_ids(user):
    """Set of campaign ids the user has saved (empty for anonymous users)."""
    if user is None or not user.is_authenticated:
        return set()
    return set(SavedCampaign.objects.filter(user=user).values_list("campaign_id", flat=True))
