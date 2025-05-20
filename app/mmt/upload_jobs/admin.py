from django.contrib import admin

from .models import UploadJob
from mmt.uploaded_files.models import UploadedFile


class UploadedFileInline(admin.TabularInline):
    model = UploadedFile
    can_delete = False
    extra = 0


@admin.register(UploadJob)
class UploadJobAdmin(admin.ModelAdmin):
    inlines = [
        UploadedFileInline,
    ]
