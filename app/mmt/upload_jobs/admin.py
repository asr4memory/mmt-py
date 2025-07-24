from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import UploadJob


@admin.register(UploadJob)
class UploadJobAdmin(admin.ModelAdmin):
    list_display = ["user", "title", "language", "created_at"]
    list_display_links = ["title"]
    list_filter = ["user", "created_at"]
    search_fields = ["title", "description", "language", "user__username"]
