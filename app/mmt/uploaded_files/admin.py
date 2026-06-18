from django.contrib import admin
from django.db.models import F, Q
from django.utils.translation import gettext_lazy as _

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
            return (
                queryset.exclude(checksum_client='')
                .exclude(checksum_server='')
                .filter(checksum_client=F('checksum_server'))
            )
        if self.value() == 'unverified':
            return queryset.filter(Q(checksum_client='') | Q(checksum_server=''))
        return queryset


@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = (
        'filename',
        'project',
        'status',
        'integrity',
        'size',
        'created_at',
    )
    list_filter = (IntegrityFilter, 'media_type', 'created_at')
    search_fields = ('filename', 'original_filename')
    readonly_fields = (
        'checksum_server',
        'checksum_client',
        'created_at',
        'updated_at',
    )

    def has_add_permission(self, request):
        # Uploaded files are created through the upload flow, never by hand.
        return False

    @admin.display(description=_('Integrity'))
    def integrity(self, obj):
        if obj.is_corrupt is None:
            return _('unverified')
        return _('corrupt') if obj.is_corrupt else _('ok')
