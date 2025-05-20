from django.urls import path

from . import views

app_name = "downloads"

urlpatterns = [
    path("", views.download_index, name="download_index"),
    path("<str:filename>/", views.download_detail, name="download_detail"),
]
