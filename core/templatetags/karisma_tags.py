from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


def _group_indian(number: int) -> str:
    """Group digits the Indian way: 1,25,000 / 12,34,56,789."""
    digits = str(number)
    if len(digits) <= 3:
        return digits
    head, tail = digits[:-3], digits[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts + [tail])


def _to_decimal(value):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        return None


@register.filter
def inr(value):
    """Format a number as Indian rupees: ₹1,25,000 (paise shown only if present)."""
    amount = _to_decimal(value)
    if amount is None:
        return value
    sign = "-" if amount < 0 else ""
    amount = abs(amount)
    whole = int(amount)
    paise = int((amount - whole) * 100)
    text = f"{sign}₹{_group_indian(whole)}"
    if paise:
        text += f".{paise:02d}"
    return text


@register.filter
def compact_inr(value):
    """Short form for big numbers: ₹2.4 Cr, ₹5.6 L."""
    amount = _to_decimal(value)
    if amount is None:
        return value
    if amount >= Decimal("10000000"):
        return f"₹{(amount / Decimal('10000000')):.1f} Cr"
    if amount >= Decimal("100000"):
        return f"₹{(amount / Decimal('100000')):.1f} L"
    return inr(amount)


@register.filter
def initials(user):
    """Two-letter initials for a user object."""
    name = (user.get_full_name() or user.username).split()
    if len(name) >= 2:
        return (name[0][0] + name[-1][0]).upper()
    return name[0][:2].upper()


@register.filter
def display_name(user):
    return user.get_full_name() or user.username


@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    """Return the current querystring with the given params replaced."""
    query = context["request"].GET.copy()
    for key, value in kwargs.items():
        query[key] = value
    return query.urlencode()


@register.filter
def in_set(value, collection):
    """Template-friendly membership test: {{ obj.pk|in_set:saved_ids }}."""
    try:
        return value in collection
    except TypeError:
        return False
