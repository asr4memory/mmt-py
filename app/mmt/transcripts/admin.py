from django.contrib import admin
from django.db.models import JSONField
from django_json_widget.widgets import JSONEditorWidget

from mmt.transcripts.models import Transcript, TranscriptionJob
from mmt.uploaded_files.models import UploadedFile


@admin.register(Transcript)
class TranscriptAdmin(admin.ModelAdmin):
    list_display = ['label', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['label']

    fields = [
        'label',
        'uploaded_file',
        'content',
        'created_at',
        'updated_at',
    ]

    readonly_fields = [
        'created_at',
        'updated_at',
    ]

    formfield_overrides = {
        JSONField: {'widget': JSONEditorWidget},
    }

    def get_queryset(self, request):
        # content can hold a large JSON document and is not part of
        # list_display. The change form still reads it, which loads the field
        # in one additional query.
        return super().get_queryset(request).defer('content')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'uploaded_file':
            kwargs['queryset'] = UploadedFile.objects.select_related('project')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(TranscriptionJob)
class TranscriptionJobAdmin(admin.ModelAdmin):
    """Read-only: jobs are created by the app and updated by the ASR sweep."""

    list_display = ['uploaded_file', 'status', 'progress', 'created_at']
    list_filter = ['status', 'created_at']
    list_select_related = ['uploaded_file']

    fields = [
        'uploaded_file',
        'transcript',
        'asr_job_id',
        'status',
        'progress',
        'error',
        'language',
        'diarize',
        'created_at',
        'updated_at',
        'started_at',
        'finished_at',
    ]
    readonly_fields = fields

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
