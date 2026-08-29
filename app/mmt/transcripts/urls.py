from django.urls import path

from . import views

app_name = 'transcripts'

urlpatterns = [
    path('<int:pk>/', views.detail, name='detail'),
    path('<int:pk>/edit/', views.edit, name='edit'),
    path('<int:pk>/json/', views.detail_json, name='detail-json'),
    path('<int:pk>/update/', views.update_json, name='update-json'),
    path('<int:pk>/enrich/', views.enrich, name='enrich'),
    path('<int:pk>/delete/', views.delete, name='delete'),
    path('<int:pk>/export/whisperx/', views.export_whisperx, name='export-whisperx'),
]
