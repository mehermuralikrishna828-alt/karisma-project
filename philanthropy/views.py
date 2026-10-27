from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import DecimalField, ExpressionWrapper, F, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView

from .models import PhilanthropyCause
from .utils import get_followed_cause_ids

QUICK_AMOUNTS = [100, 500, 1000, 2500, 5000]


class CauseListView(ListView):
    model = PhilanthropyCause
    template_name = "philanthropy/cause_list.html"
    context_object_name = "causes"
    paginate_by = 9

    SORTS = {
        "popular": "-supporters_count",
        "recent": "-created_at",
        "funded": "-funded_pct",
        "title": "title",
    }

    def get_queryset(self):
        params = self.request.GET
        qs = PhilanthropyCause.objects.filter(is_active=True).annotate(
            funded_pct=ExpressionWrapper(
                F("amount_raised") * 100 / F("target_amount"),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )
        query = params.get("q", "").strip()
        if query:
            matching = [
                value
                for value, label in PhilanthropyCause.Category.choices
                if query.lower() in label.lower()
            ]
            qs = qs.filter(
                Q(title__icontains=query)
                | Q(description__icontains=query)
                | Q(beneficiary_info__icontains=query)
                | Q(category__in=matching)
            )
        category = params.get("category", "")
        if category in PhilanthropyCause.Category.values:
            qs = qs.filter(category=category)
        sort = params.get("sort", "popular")
        return qs.order_by(self.SORTS.get(sort, "-supporters_count"), "title")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        params = self.request.GET
        context.update(
            {
                "categories": PhilanthropyCause.Category.choices,
                "followed_cause_ids": get_followed_cause_ids(self.request.user),
                "filters": {
                    "q": params.get("q", ""),
                    "category": params.get("category", ""),
                    "sort": params.get("sort", "popular"),
                },
                "has_filters": bool(params.get("q") or params.get("category")),
            }
        )
        return context


class CauseDetailView(DetailView):
    model = PhilanthropyCause
    template_name = "philanthropy/cause_detail.html"
    context_object_name = "cause"

    def get_queryset(self):
        return PhilanthropyCause.objects.filter(is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cause = self.object
        user = self.request.user
        context.update(
            {
                "supporters": cause.donations.filter(status="completed")
                .select_related("user")
                .order_by("-created_at")[:8],
                "is_following": user.is_authenticated and cause.followers.filter(pk=user.pk).exists(),
                "quick_amounts": QUICK_AMOUNTS,
                "related": PhilanthropyCause.objects.filter(is_active=True)
                .exclude(pk=cause.pk)[:3],
                "followed_cause_ids": get_followed_cause_ids(user),
            }
        )
        return context


@login_required
@require_POST
def toggle_follow(request, slug):
    cause = get_object_or_404(PhilanthropyCause, slug=slug, is_active=True)
    if cause.followers.filter(pk=request.user.pk).exists():
        cause.followers.remove(request.user)
        following = False
        message = "You unfollowed this cause."
    else:
        cause.followers.add(request.user)
        following = True
        message = "You're now following this cause."

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"saved": following, "message": message})

    messages.success(request, message)
    next_url = request.POST.get("next", "")
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect(cause.get_absolute_url())
