from django.urls import path

from . import views

app_name = "account"

urlpatterns = [
    path("profile/", views.profile, name="profile"),
    path("profile/edit/", views.edit_profile, name="edit_profile"),
    path("profile/upload-permission/", views.upload_permission, name="upload-permission"),
    path("debug/", views.debug, name="debug"),
]
