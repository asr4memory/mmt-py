from django.contrib import admin

from mmt.core.models import Notice


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ["is_active", "title_en", "title_de", "created_at"]
    list_display_links = ["title_en", "title_de"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["title_en", "title_de"]
