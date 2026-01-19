from django.urls import path

from . import views

app_name = 'uploaded_files'

urlpatterns = [
    path('<int:pk>/', views.detail, name='detail'),
    path('<int:pk>/download/', views.download, name='download'),
    path('<int:pk>/upload/', views.upload, name='upload'),
    path('<int:pk>/update/', views.update, name='update'),
    path('<int:pk>/delete/', views.delete, name='delete'),
    path(
        '<int:pk>/create-transcript/', views.transcript_create, name='create-transcript'
    ),
]
