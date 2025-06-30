from django.urls import path

from . import views

app_name = "upload_jobs"

urlpatterns = [
    path("", views.index, name="index"),
    path("create/", views.create, name="create"),
    path("<int:pk>/", views.detail, name="detail"),
    path(
        "<int:pk>/file/<int:uploaded_file_pk>",
        views.uploaded_file_detail,
        name="uploaded-file-detail",
    ),
    path("<int:pk>/delete/", views.delete, name="delete"),
    path(
        "<int:pk>/create-file/", views.create_uploaded_file, name="create_uploaded_file"
    ),
]
