from django.urls import path

from . import views

app_name = "projects"

urlpatterns = [
    path("", views.project_index, name="index"),
    path("create/", views.project_create, name="create"),
    path("<int:pk>/", views.project_detail, name="detail"),
    path("<int:pk>/settings/", views.project_settings, name="settings"),
    path("<int:pk>/delete/", views.project_delete, name="delete"),
    path("<int:pk>/upload/", views.upload, name="upload"),
    path("<int:pk>/create-file/", views.create_uploaded_file, name="create-file"),
    path(
        "<int:project_pk>/uploads/<int:uploaded_file_pk>/",
        views.uploaded_file_detail,
        name="uploaded-file-detail",
    ),
    path(
        "<int:pk>/processing-requests/create/",
        views.processing_request_create,
        name="create-processing-request",
    ),
    path(
        "<int:project_pk>/processing-requests/<int:pk>/",
        views.processing_request_detail,
        name="processing-request",
    ),
    path(
        "<int:pk>/downloads/<str:filename>/",
        views.download_detail,
        name="download_detail",
    ),
]
