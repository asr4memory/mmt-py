from django.urls import path

from . import views

app_name = 'transcripts'

urlpatterns = [
    path('create/', views.transcript_create, name='create'),
    path('<int:pk>/edit/', views.transcript_edit, name='edit'),
    path('<int:pk>/json/', views.transcript_json, name='json'),
]
