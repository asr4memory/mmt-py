from django.urls import path

from . import views

app_name = 'transcripts'

urlpatterns = [
    path('<int:pk>/', views.detail, name='detail'),
    path('<int:pk>/edit/', views.edit, name='edit'),
    path('<int:pk>/json/', views.json, name='json'),
    path('<int:pk>/delete/', views.delete, name='delete'),
]
