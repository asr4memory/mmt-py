from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from mmt.projects.models import ProcessingRequest, Project
from mmt.projects.tasks import send_processing_request_updated_email
from mmt.uploaded_files.models import UploadedFile


class UploadedFileInline(admin.TabularInline):
    fields = ['filename', 'has_file', 'media_type', 'formatted_size', 'created_at']
    readonly_fields = [
        'filename',
        'has_file',
        'formatted_size',
        'media_type',
        'created_at',
    ]
    ordering = ['-created_at']

    model = UploadedFile
    can_delete = True
    extra = 0

    def has_add_permission(self, request, obj):
        """Do not show add link."""
        return False

    def formatted_size(self, obj):
        if not obj.size:
            return '-'
        size = obj.size
        for unit in ['bytes', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f'{size:.1f} {unit}'
            size /= 1024.0

    formatted_size.short_description = _('Size')


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'created_at']
    list_display_links = ['title']
    list_filter = ['user', 'created_at']
    search_fields = ['title', 'description', 'user__username']
    fields = ['title', 'user', 'description', 'downloadable_files_count']
    readonly_fields = ['user', 'downloadable_files_count']
    inlines = [UploadedFileInline]


@admin.register(ProcessingRequest)
class ProcessingRequestAdmin(admin.ModelAdmin):
    list_display = ['project__user', 'project', 'created_at', 'status']
    list_display_links = ['created_at']
    list_filter = ['project__user', 'project', 'created_at', 'status']
    search_fields = ['project__user__username', 'description', 'admin_comment']

    fields = [
        'user_link',
        'project',
        'created_at',
        'status',
        'description',
        'admin_comment',
        'language',
        'make_available_on_platform',
        'replace_existing_files',
        'check_media_files',
        'transcribe',
        'uploaded_files',
    ]
    readonly_fields = [
        'user_link',
        'project',
        'created_at',
        'description',
        'language',
        'make_available_on_platform',
        'replace_existing_files',
        'check_media_files',
        'transcribe',
        'uploaded_files',
    ]

    def user_link(self, obj):
        user = obj.project.user
        url = reverse('admin:my_account_user_change', args=[user.id])
        return format_html(
            '{} &lt;{}&gt; <a href="{}">{}</a>',
            user.username,
            user.email,
            url,
            _('View user'),
        )

    user_link.short_description = _('User')

    def save_model(self, request, obj, form, change):
        field = 'status'
        super().save_model(request, obj, form, change)
        if change and field in form.changed_data:
            send_processing_request_updated_email.delay(obj.id)
