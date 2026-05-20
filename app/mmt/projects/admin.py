from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from mmt.core.utils import format_duration
from mmt.projects.models import ProcessingRequest, Project
from mmt.projects.tasks import send_processing_request_updated_email
from mmt.uploaded_files.models import UploadedFile


class UploadedFileInline(admin.TabularInline):
    fields = [
        'filename',
        'has_file',
        'media_type',
        'formatted_size',
        'formatted_duration',
        'has_waveform',
        'created_at',
    ]
    readonly_fields = [
        'filename',
        'has_file',
        'formatted_size',
        'formatted_duration',
        'media_type',
        'has_waveform',
        'created_at',
    ]
    ordering = ['-created_at']

    model = UploadedFile

    @admin.display(boolean=True, description=_('Waveform?'))
    def has_waveform(self, obj):
        return obj.has_waveform

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

    def formatted_duration(self, obj):
        if obj.duration == 0:
            return ''
        else:
            return format_duration(obj.duration)

    formatted_duration.short_description = _('Duration')


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
        'uploaded_files_count',
        'uploaded_files_list',
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
        'uploaded_files_count',
        'uploaded_files_list',
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

    def uploaded_files_list(self, obj):
        sorted_files = sorted(obj.uploaded_files, key=str.lower)

        item = '<li>{}</li>'
        items = item * len(sorted_files)
        all = '<ul style="margin: 0; padding: 0;">' + items + '</ul>'

        return format_html(
            all,
            *sorted_files,
        )

    uploaded_files_list.short_description = _('Uploaded files')

    def save_model(self, request, obj, form, change):
        field = 'status'
        super().save_model(request, obj, form, change)
        if change and field in form.changed_data:
            send_processing_request_updated_email.delay(obj.id)
