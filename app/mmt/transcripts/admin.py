from django.contrib import admin
from django.db.models import JSONField
from django_json_widget.widgets import JSONEditorWidget

from mmt.transcripts.models import Transcript


@admin.register(Transcript)
class TranscriptAdmin(admin.ModelAdmin):
    list_display = ['label', 'language', 'created_at']
    list_filter = ['language', 'created_at']
    search_fields = ['label']

    fields = [
        'label',
        'uploaded_file',
        'language',
        'content',
    ]

    formfield_overrides = {
        JSONField: {'widget': JSONEditorWidget},
    }
