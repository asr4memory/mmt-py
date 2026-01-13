from django.urls import path

from . import views

app_name = 'transcripts'

urlpatterns = [
    path('<int:pk>/', views.transcript_detail, name='detail'),
    path('<int:pk>/json/', views.transcript_json, name='json'),
]
