from django.urls import path

from . import views

app_name = "account"

urlpatterns = [
    path("profile/", views.profile, name="profile"),
    path("profile/edit/", views.edit_profile, name="edit_profile"),
    path("register/", views.register, name="register"),
    path(
        "register/complete/", views.registration_complete, name="registration_complete"
    ),
]
