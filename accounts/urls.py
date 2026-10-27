from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.KarismaLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("password/", views.KarismaPasswordChangeView.as_view(), name="password_change"),
    path("u/<str:username>/", views.public_profile, name="profile"),
]
