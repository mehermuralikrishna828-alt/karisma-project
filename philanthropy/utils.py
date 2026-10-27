from .models import PhilanthropyCause


def get_followed_cause_ids(user):
    if user is None or not user.is_authenticated:
        return set()
    return set(
        PhilanthropyCause.objects.filter(followers=user).values_list("pk", flat=True)
    )
