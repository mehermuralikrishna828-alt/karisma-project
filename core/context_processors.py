NAV_ITEMS = [
    {"key": "home", "label": "Home", "icon": "bi-house-heart", "url": "core:home"},
    {"key": "crowdfunding", "label": "Crowdfunding", "icon": "bi-rocket-takeoff", "url": "crowdfunding:list"},
    {"key": "donations", "label": "Donations", "icon": "bi-box2-heart", "url": "donations:index"},
    {"key": "philanthropy", "label": "Philanthropy", "icon": "bi-globe-central-south-asia", "url": "philanthropy:list"},
    {"key": "dashboard", "label": "Dashboard", "icon": "bi-grid-1x2", "url": "dashboard:home"},
]

NAMESPACE_TO_NAV = {
    "core": "home",
    "crowdfunding": "crowdfunding",
    "donations": "donations",
    "philanthropy": "philanthropy",
    "dashboard": "dashboard",
}


def karisma(request):
    """Expose navigation state and unread notification count to all templates."""
    match = getattr(request, "resolver_match", None)
    namespace = match.namespace if match else ""
    context = {
        "nav_items": NAV_ITEMS,
        "active_nav": NAMESPACE_TO_NAV.get(namespace, ""),
        "unread_count": 0,
    }
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        context["unread_count"] = user.notifications.filter(is_read=False).count()
    return context
