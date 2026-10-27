from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView

from crowdfunding.models import Campaign
from crowdfunding.utils import get_saved_campaign_ids

from .forms import KarismaPasswordChangeForm, LoginForm, RegisterForm
from .models import Notification
from .utils import notify

User = get_user_model()


class RegisterView(CreateView):
    form_class = RegisterForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("dashboard:home")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("dashboard:home")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        notify(
            self.object,
            Notification.Kind.SYSTEM,
            "Welcome to Karisma!",
            "Your account is ready. Explore campaigns, donate items or support a cause.",
            reverse("crowdfunding:list"),
        )
        messages.success(self.request, f"Welcome to Karisma, {self.object.first_name}!")
        return response


class KarismaLoginView(LoginView):
    authentication_form = LoginForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        messages.success(self.request, f"Welcome back, {form.get_user().first_name or form.get_user().username}!")
        return super().form_valid(form)


class KarismaPasswordChangeView(LoginRequiredMixin, SuccessMessageMixin, PasswordChangeView):
    form_class = KarismaPasswordChangeForm
    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("dashboard:settings")
    success_message = "Your password was updated."


def public_profile(request, username):
    profile_user = get_object_or_404(User, username=username, is_active=True)
    campaigns = (
        Campaign.objects.filter(creator=profile_user)
        .exclude(status=Campaign.Status.CANCELLED)
        .order_by("-created_at")
    )
    return render(
        request,
        "accounts/profile.html",
        {
            "profile_user": profile_user,
            "campaigns": campaigns,
            "saved_campaign_ids": get_saved_campaign_ids(request.user),
        },
    )
