from django.urls import path

from . import views

app_name = "uploaded_files"

urlpatterns = [
    path("<int:pk>/upload/", views.upload, name="upload"),
    path("<int:pk>/upload-chunk/<int:chunk>", views.upload_chunk, name="upload-chunk"),
    path("<int:pk>/update/", views.update, name="update"),
    path("<int:pk>/delete/", views.delete, name="delete"),
]
