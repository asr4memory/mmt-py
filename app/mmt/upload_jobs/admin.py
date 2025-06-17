from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import UploadJob
from mmt.uploaded_files.models import UploadedFile


class UploadedFileInline(admin.TabularInline):
    readonly_fields = ["filename", "formatted_size", "media_type"]
    exclude = ["checksum_client", "size", "checksum_server", "transferred"]

    model = UploadedFile
    can_delete = True
    extra = 0

    def has_add_permission(self, request, obj):
        """Do not show add link."""
        return False

    def formatted_size(self, obj):
        if not obj.size:
            return "-"
        size = obj.size
        for unit in ["bytes", "KB", "MB", "GB", "TB"]:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0

    formatted_size.short_description = _("Size")


@admin.register(UploadJob)
class UploadJobAdmin(admin.ModelAdmin):
    list_display = ["user", "title", "language", "created_at"]
    list_display_links = ["title"]
    list_filter = ["user", "created_at"]
    search_fields = ["title", "description", "language", "user__username"]
    inlines = [
        UploadedFileInline,
    ]
