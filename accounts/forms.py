from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    UserCreationForm,
)

from core.forms import BootstrapFormMixin

from .models import Profile

User = get_user_model()


class RegisterForm(BootstrapFormMixin, UserCreationForm):
    first_name = forms.CharField(max_length=50, label="First name")
    last_name = forms.CharField(max_length=50, label="Last name")
    email = forms.EmailField(label="Email address")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("first_name", "last_name", "username", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    pass


class KarismaPasswordChangeForm(BootstrapFormMixin, PasswordChangeForm):
    pass


class UserForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This email is already used by another account.")
        return email


class ProfileForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Profile
        fields = ("phone", "city", "state", "bio", "avatar")
        widgets = {"bio": forms.Textarea(attrs={"rows": 3})}

    def clean_avatar(self):
        avatar = self.cleaned_data.get("avatar")
        if avatar and hasattr(avatar, "size") and avatar.size > 2 * 1024 * 1024:
            raise forms.ValidationError("Please upload an image smaller than 2 MB.")
        return avatar
