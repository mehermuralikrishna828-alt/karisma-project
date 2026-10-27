from django.urls import path

from . import views

app_name = "philanthropy"

urlpatterns = [
    path("", views.CauseListView.as_view(), name="list"),
    path("<slug:slug>/", views.CauseDetailView.as_view(), name="detail"),
    path("<slug:slug>/follow/", views.toggle_follow, name="toggle_follow"),
]
