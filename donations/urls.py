from django.urls import path

from . import views

app_name = "donations"

urlpatterns = [
    path("", views.index, name="index"),
    path("category/<slug:slug>/", views.category_detail, name="category"),
    path("donate/<str:kind>/<slug:slug>/<str:step>/", views.money_flow, name="flow"),
    path("success/<str:reference>/", views.success, name="success"),
]
