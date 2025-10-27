from django.urls import path

from . import views

app_name = "account"

urlpatterns = [
    path("profile/", views.profile, name="profile"),
    path("profile/edit/", views.edit_profile, name="edit_profile"),
    path("debug/", views.debug, name="debug"),
]
