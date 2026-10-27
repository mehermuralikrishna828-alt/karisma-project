from django.urls import path

from . import views

app_name = "crowdfunding"

urlpatterns = [
    path("", views.CampaignListView.as_view(), name="list"),
    path("create/", views.CampaignCreateView.as_view(), name="create"),
    path("c/<slug:slug>/", views.CampaignDetailView.as_view(), name="detail"),
    path("c/<slug:slug>/edit/", views.CampaignEditView.as_view(), name="edit"),
    path("c/<slug:slug>/delete/", views.CampaignDeleteView.as_view(), name="delete"),
    path("c/<slug:slug>/update/", views.post_update, name="post_update"),
    path("c/<slug:slug>/save/", views.toggle_save, name="toggle_save"),
]
