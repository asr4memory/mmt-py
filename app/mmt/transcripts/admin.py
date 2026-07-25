from django.contrib import admin
from django.db.models import JSONField
from django_json_widget.widgets import JSONEditorWidget

from mmt.transcripts.models import Transcript
from mmt.uploaded_files.models import UploadedFile


@admin.register(Transcript)
class TranscriptAdmin(admin.ModelAdmin):
    list_display = ['label', 'created_at']
    list_filter = ['created_at']
    search_fields = ['label']

    fields = [
        'label',
        'uploaded_file',
        'content',
    ]

    formfield_overrides = {
        JSONField: {'widget': JSONEditorWidget},
    }

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'uploaded_file':
            kwargs['queryset'] = UploadedFile.objects.select_related('project')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
