from django.contrib import admin
from django.template.defaultfilters import filesizeformat
from django.utils.html import format_html
from django.utils.text import Truncator
from django.utils.translation import gettext_lazy as _

from mmt.core.utils import format_duration
from mmt.uploaded_files.models import UploadedFile


class IntegrityFilter(admin.SimpleListFilter):
    title = _('integrity')
    parameter_name = 'integrity'

    def lookups(self, request, model_admin):
        return [
            ('corrupt', _('Corrupt (checksums differ)')),
            ('ok', _('OK (checksums match)')),
            ('unverified', _('Unverified (checksum missing)')),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'corrupt':
            return queryset.corrupt()
        if self.value() == 'ok':
            return queryset.checksum_ok()
        if self.value() == 'unverified':
            return queryset.unverified()
        return queryset


class UploadedFileDisplayMixin:
    """Shared admin display methods for :class:`UploadedFile`.

    Used by both :class:`UploadedFileAdmin` and the ``UploadedFileInline`` in
    the projects admin so the two render the same list columns identically.
    """

    @admin.display(description=_('Size'), ordering='size')
    def size_display(self, obj):
        if not obj.size:
            return '-'
        return filesizeformat(obj.size)

    @admin.display(description=_('Duration'), ordering='duration')
    def duration_display(self, obj):
        if obj.duration == 0:
            return '-'
        return format_duration(obj.duration)

    @admin.display(description=_('Integrity'))
    def integrity(self, obj):
        if obj.is_corrupt is None:
            return _('unverified')
        return _('corrupt') if obj.is_corrupt else _('ok')


@admin.register(UploadedFile)
class UploadedFileAdmin(UploadedFileDisplayMixin, admin.ModelAdmin):
    list_display = (
        'filename_display',
        'project',
        'status',
        'integrity',
        'media_type',
        'size_display',
        'duration_display',
        'created_at',
        'updated_at',
    )
    list_filter = (IntegrityFilter, 'media_type', 'created_at')
    search_fields = ('filename', 'original_filename')
    ordering = ('-created_at',)
    exclude = ('size', 'duration')
    readonly_fields = (
        'project',
        'filename',
        'original_filename',
        'has_file',
        'assembling',
        'status',
        'integrity',
        'size_display',
        'media_type',
        'duration_display',
        'has_waveform_display',
        'has_web_video',
        'checksum_server',
        'checksum_client',
        'created_at',
        'updated_at',
    )

    @admin.display(description=_('Filename'), ordering='filename')
    def filename_display(self, obj):
        # The changelist auto-links its first column to the change page.
        return format_html(
            '<span title="{}">{}</span>',
            obj.filename,
            Truncator(obj.filename).chars(60),
        )

    @admin.display(boolean=True, description=_('Waveform?'))
    def has_waveform_display(self, obj):
        return obj.has_waveform

    def has_add_permission(self, request):
        # Uploaded files are created through the upload flow, never by hand.
        return False
