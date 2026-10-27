from .models import Notification, Profile


def notify(user, kind, title, message="", link=""):
    """Create an in-app notification (no-op for missing users)."""
    if user is None:
        return None
    return Notification.objects.create(
        user=user, kind=kind, title=title[:140], message=message[:500], link=link[:300]
    )


def get_profile(user):
    """Return the user's Profile, creating it if it is somehow missing."""
    profile, _ = Profile.objects.get_or_create(user=user)
    return profile
