from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.db.models import DecimalField, ExpressionWrapper, F, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from accounts.models import Notification
from accounts.utils import notify

from .forms import CampaignEditForm, CampaignForm, CampaignUpdateForm
from .models import Campaign, SavedCampaign
from .services import notify_campaign_update
from .utils import get_saved_campaign_ids

QUICK_AMOUNTS = [250, 500, 1000, 2500, 5000]


class CampaignListView(ListView):
    model = Campaign
    template_name = "crowdfunding/campaign_list.html"
    context_object_name = "campaigns"
    paginate_by = 9

    SORTS = {
        "recent": "-created_at",
        "popular": "-contributors_count",
        "deadline": "deadline",
        "funded": "-funded_pct",
    }

    def get_queryset(self):
        params = self.request.GET
        today = timezone.localdate()
        qs = (
            Campaign.objects.exclude(status=Campaign.Status.CANCELLED)
            .select_related("creator", "creator__profile")
            .annotate(
                funded_pct=ExpressionWrapper(
                    F("amount_raised") * 100 / F("target_amount"),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                )
            )
        )

        query = params.get("q", "").strip()
        if query:
            matching_categories = [
                value for value, label in Campaign.Category.choices if query.lower() in label.lower()
            ]
            qs = qs.filter(
                Q(title__icontains=query)
                | Q(short_description__icontains=query)
                | Q(description__icontains=query)
                | Q(location__icontains=query)
                | Q(category__in=matching_categories)
            )

        category = params.get("category", "")
        if category in Campaign.Category.values:
            qs = qs.filter(category=category)

        status = params.get("status", "")
        if status == "active":
            qs = qs.filter(status=Campaign.Status.ACTIVE, deadline__gte=today)
        elif status == "funded":
            qs = qs.filter(status=Campaign.Status.FUNDED)
        elif status == "ending":
            qs = qs.filter(
                status=Campaign.Status.ACTIVE,
                deadline__gte=today,
                deadline__lte=today + timedelta(days=7),
            )
        elif status == "ended":
            qs = qs.filter(
                Q(status=Campaign.Status.CLOSED)
                | Q(status=Campaign.Status.ACTIVE, deadline__lt=today)
            )

        if params.get("verified") == "1":
            qs = qs.filter(is_verified=True)

        sort = params.get("sort", "recent")
        return qs.order_by(self.SORTS.get(sort, "-created_at"), "-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        params = self.request.GET
        context.update(
            {
                "categories": Campaign.Category.choices,
                "saved_campaign_ids": get_saved_campaign_ids(self.request.user),
                "filters": {
                    "q": params.get("q", ""),
                    "category": params.get("category", ""),
                    "status": params.get("status", ""),
                    "sort": params.get("sort", "recent"),
                    "verified": params.get("verified", ""),
                },
                "has_filters": any(
                    params.get(k) for k in ("q", "category", "status", "verified")
                ),
            }
        )
        return context


class CampaignDetailView(DetailView):
    model = Campaign
    template_name = "crowdfunding/campaign_detail.html"
    context_object_name = "campaign"

    def get_queryset(self):
        return Campaign.objects.select_related("creator", "creator__profile")

    def get_object(self, queryset=None):
        campaign = super().get_object(queryset)
        if campaign.status == Campaign.Status.CANCELLED and campaign.creator_id != self.request.user.id:
            raise Http404("This campaign has been cancelled.")
        return campaign

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        campaign = self.object
        user = self.request.user
        supporters = (
            campaign.donations.filter(status="completed")
            .select_related("user")
            .order_by("-created_at")
        )
        context.update(
            {
                "updates": campaign.updates.all(),
                "contributors": supporters[:10],
                "is_owner": user.is_authenticated and campaign.creator_id == user.id,
                "is_saved": user.is_authenticated
                and SavedCampaign.objects.filter(user=user, campaign=campaign).exists(),
                "quick_amounts": QUICK_AMOUNTS,
                "update_form": CampaignUpdateForm()
                if user.is_authenticated and campaign.creator_id == user.id
                else None,
                "creator_campaign_count": Campaign.objects.filter(creator=campaign.creator)
                .exclude(status=Campaign.Status.CANCELLED)
                .count(),
                "saved_campaign_ids": get_saved_campaign_ids(user),
                "similar": Campaign.objects.filter(
                    category=campaign.category, status=Campaign.Status.ACTIVE
                )
                .exclude(pk=campaign.pk)
                .select_related("creator")[:3],
            }
        )
        return context


class CampaignCreateView(LoginRequiredMixin, CreateView):
    model = Campaign
    form_class = CampaignForm
    template_name = "crowdfunding/campaign_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"page_title": "Start a campaign", "submit_label": "Launch campaign"})
        return context

    def form_valid(self, form):
        form.instance.creator = self.request.user
        response = super().form_valid(form)
        notify(
            self.request.user,
            Notification.Kind.CAMPAIGN,
            "Your campaign is live",
            f"“{self.object.title}” is now open for support.",
            self.object.get_absolute_url(),
        )
        messages.success(
            self.request, "Your campaign is live! Share it with friends and family to get started."
        )
        return response


class OwnerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Only the creator of a campaign may edit or delete it."""

    def test_func(self):
        return self.get_object().creator_id == self.request.user.id


class CampaignEditView(OwnerRequiredMixin, UpdateView):
    model = Campaign
    form_class = CampaignEditForm
    template_name = "crowdfunding/campaign_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"page_title": "Edit campaign", "submit_label": "Save changes"})
        return context

    def form_valid(self, form):
        messages.success(self.request, "Campaign updated.")
        return super().form_valid(form)


class CampaignDeleteView(OwnerRequiredMixin, DeleteView):
    model = Campaign
    template_name = "crowdfunding/campaign_confirm_delete.html"
    success_url = reverse_lazy("dashboard:campaigns")

    def post(self, request, *args, **kwargs):
        campaign = self.get_object()
        if campaign.donations.exists():
            messages.error(
                request,
                "This campaign already has donations, so it can't be deleted. "
                "You can close or cancel it from the edit page instead.",
            )
            return redirect(campaign.get_absolute_url())
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, "Campaign deleted.")
        return super().form_valid(form)


@login_required
@require_POST
def post_update(request, slug):
    campaign = get_object_or_404(Campaign, slug=slug)
    if campaign.creator_id != request.user.id:
        raise PermissionDenied
    form = CampaignUpdateForm(request.POST)
    if form.is_valid():
        update = form.save(commit=False)
        update.campaign = campaign
        update.save()
        notify_campaign_update(update)
        messages.success(request, "Update posted. Your supporters have been notified.")
    else:
        messages.error(request, "Please provide both a title and the update text.")
    return redirect(campaign.get_absolute_url() + "#updates")


@login_required
@require_POST
def toggle_save(request, slug):
    campaign = get_object_or_404(Campaign, slug=slug)
    saved_item, created = SavedCampaign.objects.get_or_create(user=request.user, campaign=campaign)
    if not created:
        saved_item.delete()
    message = "Campaign saved to your dashboard." if created else "Campaign removed from saved."

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"saved": created, "message": message})

    messages.success(request, message)
    next_url = request.POST.get("next", "")
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect(campaign.get_absolute_url())
