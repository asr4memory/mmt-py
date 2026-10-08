from math import ceil

from django.conf import settings
from django.contrib import admin
from django.template.defaultfilters import filesizeformat
from django.utils.translation import gettext_lazy as _

from mmt.core.admin_display import truncated
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

    @admin.display(description=_('Original filename'), ordering='original_filename')
    def original_filename_display(self, obj):
        return truncated(obj.original_filename)

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
        'original_filename_display',
        'project__user',
        'project_display',
        'status',
        'integrity',
        'media_type',
        'size_display',
        'duration_display',
        'created_at',
        'updated_at',
    )
    list_filter = (
        'project__user',
        IntegrityFilter,
        'media_type',
        'created_at',
        'updated_at',
    )
    list_select_related = ('project', 'project__user')
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
        'chunks_display',
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
        return truncated(obj.filename)

    @admin.display(description=_('Project'), ordering='project__title')
    def project_display(self, obj):
        return truncated(obj.project.title, 40)

    @admin.display(boolean=True, description=_('Waveform?'))
    def has_waveform_display(self, obj):
        return obj.has_waveform

    @admin.display(description=_('Chunks'))
    def chunks_display(self, obj):
        received = obj.chunks.count()
        if not received or not obj.size:
            return '-'
        return _('%(received)d of %(total)d (%(percent)d %%)') % {
            'received': received,
            'total': ceil(obj.size / settings.MMT_UPLOAD_CHUNK_SIZE),
            'percent': obj.transferred_from_chunks() * 100 // obj.size,
        }

    def has_add_permission(self, request):
        # Uploaded files are created through the upload flow, never by hand.
        return False
