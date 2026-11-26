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
    path(
        '<int:pk>/export/',
        views.export_page,
        {'template': 'transcripts/export/index.html'},
        name='export',
    ),
    path(
        '<int:pk>/export/word-processor/',
        views.export_page,
        {'template': 'transcripts/export/word_processor.html'},
        name='export-word-processor',
    ),
    path(
        '<int:pk>/export/reading/',
        views.export_page,
        {'template': 'transcripts/export/reading.html'},
        name='export-reading',
    ),
    path(
        '<int:pk>/export/spreadsheet/',
        views.export_page,
        {'template': 'transcripts/export/spreadsheet.html'},
        name='export-spreadsheet',
    ),
    path(
        '<int:pk>/export/subtitles/',
        views.export_page,
        {'template': 'transcripts/export/subtitles.html'},
        name='export-subtitles',
    ),
    path(
        '<int:pk>/export/maxqda/',
        views.export_page,
        {'template': 'transcripts/export/maxqda.html'},
        name='export-maxqda',
    ),
    path(
        '<int:pk>/export/oral-history-digital/',
        views.export_page,
        {'template': 'transcripts/export/oral_history_digital.html'},
        name='export-oral-history-digital',
    ),
    path(
        '<int:pk>/export/digital-edition/',
        views.export_page,
        {'template': 'transcripts/export/digital_edition.html'},
        name='export-digital-edition',
    ),
    path(
        '<int:pk>/export/data/',
        views.export_page,
        {'template': 'transcripts/export/data.html'},
        name='export-data',
    ),
    path(
        '<int:pk>/export/backup/',
        views.export_page,
        {'template': 'transcripts/export/backup.html'},
        name='export-backup',
    ),
    path('<int:pk>/export/mmt/', views.export_mmt, name='export-mmt'),
    path('<int:pk>/export/whisperx/', views.export_whisperx, name='export-whisperx'),
    path('<int:pk>/export/vtt/', views.export_vtt, name='export-vtt'),
    path('<int:pk>/export/srt/', views.export_srt, name='export-srt'),
    path('<int:pk>/export/csv/', views.export_csv, name='export-csv'),
    path('<int:pk>/export/tei/', views.export_tei, name='export-tei'),
    path('<int:pk>/export/pdf/', views.export_pdf, name='export-pdf'),
    path('<int:pk>/export/entities/', views.export_entities, name='export-entities'),
]
