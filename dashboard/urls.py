from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("history/", views.history, name="history"),
    path("campaigns/", views.my_campaigns, name="campaigns"),
    path("saved/", views.saved, name="saved"),
    path("notifications/", views.notifications, name="notifications"),
    path("notifications/read-all/", views.notifications_read_all, name="notifications_read_all"),
    path("notifications/<int:pk>/open/", views.notification_open, name="notification_open"),
    path("settings/", views.settings_view, name="settings"),
]
